"""Shared helpers for the github-to-cv scripts.

Standard library only. Optional libraries (pdfminer.six, pypdf) are used for
PDF text extraction when they are installed, with the `pdftotext` CLI as a
fallback.
"""
from __future__ import annotations

import json
import math
import re
import shutil
import subprocess
import sys
import zipfile
from datetime import date, datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

# Windows consoles default to cp1252, which cannot print "✓"/"→"; never crash on output.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

SCRIPTS_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPTS_DIR.parent
DATA_DIR = SCRIPTS_DIR / "data"
TEMPLATES_DIR = SKILL_DIR / "templates"

# ----------------------------------------------------------------------------
# JSON / IO
# ----------------------------------------------------------------------------

def load_json(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def save_json(obj, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    return path


def eprint(*args):
    print(*args, file=sys.stderr)


# ----------------------------------------------------------------------------
# Skills taxonomy and matching
# ----------------------------------------------------------------------------

_BOUND_L = r"(?<![A-Za-z0-9_+#])"
_BOUND_R = r"(?![A-Za-z0-9_+#])"


def _alias_pattern(alias: str) -> str:
    # Let "scikit learn" match "scikit-learn" / "scikit  learn" and vice versa.
    out = []
    for part in re.split(r"([ \-])", alias):
        if part == " ":
            out.append(r"[\s\-]+")
        elif part == "-":
            out.append(r"[\s\-]?")
        else:
            out.append(re.escape(part))
    return _BOUND_L + "".join(out) + _BOUND_R


class Taxonomy:
    """Loads skills_taxonomy.json and finds canonical skills in free text."""

    def __init__(self, path=None):
        path = path or DATA_DIR / "skills_taxonomy.json"
        raw = load_json(path)
        self.entries = []          # list of dicts {name, category, regex}
        self.by_name = {}
        self.language_map = raw.get("githubLanguageMap", {})
        self.implies = {k: v for k, v in raw.get("implies", {}).items() if not k.startswith("_")}
        self.noise_languages = set(raw.get("noiseLanguages", []))
        for category, items in raw["categories"].items():
            for item in items:
                if isinstance(item, str):
                    item = {"n": item}
                name = item["n"]
                aliases = [name] + list(item.get("a", []))
                flags = 0 if item.get("cs") else re.IGNORECASE
                if item.get("p"):
                    # A custom pattern is authoritative; "a" is documentation only.
                    pattern = item["p"]
                else:
                    pattern = "|".join(_alias_pattern(a) for a in sorted(set(aliases), key=len, reverse=True))
                entry = {"name": name, "category": category, "regex": re.compile(pattern, flags)}
                self.entries.append(entry)
                self.by_name[name.lower()] = entry

    def category_of(self, name):
        e = self.by_name.get(str(name).lower())
        return e["category"] if e else None

    def canonical(self, name):
        """Return the canonical spelling for a skill name if known."""
        e = self.by_name.get(str(name).lower())
        if e:
            return e["name"]
        for e in self.entries:
            if e["regex"].fullmatch(str(name)):
                return e["name"]
        return None

    def find(self, text: str) -> dict:
        """Return {canonical_name: occurrences} for skills mentioned in text.

        Longest match wins: "GitHub Actions" does not also count as "GitHub",
        "Docker Compose" does not also count as "Docker".
        """
        found = {}
        if not text:
            return found
        spans = []
        for e in self.entries:
            for m in e["regex"].finditer(text):
                if m.end() > m.start():
                    spans.append((m.start(), m.end(), e["name"]))
        spans.sort(key=lambda s: (-(s[1] - s[0]), s[0]))
        taken = []
        for start, end, name in spans:
            if any(start < te and ts < end and tn != name for ts, te, tn in taken):
                continue
            taken.append((start, end, name))
            found[name] = found.get(name, 0) + 1
        return found

    def map_github_language(self, lang):
        if lang in self.language_map:
            return self.language_map[lang]
        return self.canonical(lang) or lang


_TAXONOMY = None


def taxonomy() -> Taxonomy:
    global _TAXONOMY
    if _TAXONOMY is None:
        _TAXONOMY = Taxonomy()
    return _TAXONOMY


SOFT_CATEGORY = "Soft Skills"

# ----------------------------------------------------------------------------
# Job description parsing
# ----------------------------------------------------------------------------

STOPWORDS = set("""
a about above across after again against all also am an and any are as at be because been before being below between both but by can
could did do does doing down during each either etc few for from further had has have having he her here hers him his how i if in into
is it its itself just me more most my no nor not now of off on once only or other our ours out over own per same she should so some
such than that the their theirs them then there these they this those through to too under until up very via was we were what when
where which while who whom why will with within without would you your yours yourself able across along among including include
includes well work working works team teams role roles job company years year experience experienced strong good great excellent ability
skills skill knowledge understanding using use used new help build building make making based like etc e.g i.e must preferred plus
bonus nice have has we're you'll you're we'll our us looking candidate candidates opportunity join responsibilities requirements
qualifications minimum required requires requirement degree related field equivalent practical hands hands-on proven track record
environment environments fast-paced paced day days across within world class world-class best way ways part full time full-time
apply application applications benefits salary location remote hybrid office one two three four five six seven eight nine ten
end thousands millions billions behind across ensure etc. you'll we're they're
""".split())

_PREF_LINE = re.compile(r"\b(nice[\s-]to[\s-]have|preferred|bonus|a plus|is a plus|are a plus|desirable|good[\s-]to[\s-]have|would be great|ideally|not required)\b", re.I)
_PREF_HEAD = re.compile(r"^\W*(nice[\s-]to[\s-]haves?|preferred( qualifications| skills)?|bonus( points)?|good[\s-]to[\s-]have|desirable|pluses|extra credit)\W*$", re.I)
_REQ_HEAD = re.compile(r"^\W*(requirements|qualifications|basic qualifications|minimum qualifications|must[\s-]haves?|what you('|’)ll need|what you bring|you have|you will have|what we('|’)re looking for|who you are|skills|required skills|responsibilities|what you('|’)ll do|about the role|key skills)\W*$", re.I)
_YEARS = re.compile(r"(\d{1,2})\s*(?:\+|plus)?\s*(?:-|–|to)?\s*(?:\d{1,2})?\s*\+?\s*years?", re.I)
_DEGREE = re.compile(r"\b(Ph\.?D|Doctorate|Master'?s|M\.?S\.?c?|M\.?Tech|MBA|Bachelor'?s|B\.?S\.?c?|B\.?Tech|B\.?E\.?|BCA|MCA|degree)\b", re.I)


def parse_jd(text: str, tax: Taxonomy | None = None) -> dict:
    """Extract structured signals from a job description."""
    tax = tax or taxonomy()
    text = text or ""
    lines = [l.rstrip() for l in text.splitlines()]
    required, preferred = [], []
    mode = "required"
    for line in lines:
        s = line.strip()
        if not s:
            continue
        short = len(s) <= 60 and not s.endswith(".")
        if short and _PREF_HEAD.match(s.rstrip(":")):
            mode = "preferred"
            continue
        if short and _REQ_HEAD.match(s.rstrip(":")):
            mode = "required"
            continue
        if _PREF_LINE.search(s) or mode == "preferred":
            preferred.append(s)
        else:
            required.append(s)

    req_hits = tax.find("\n".join(required))
    pref_hits = tax.find("\n".join(preferred))
    skills = {}
    for name, n in req_hits.items():
        skills[name] = {"name": name, "category": tax.category_of(name), "count": n, "priority": "required"}
    for name, n in pref_hits.items():
        if name in skills:
            skills[name]["count"] += n
        else:
            skills[name] = {"name": name, "category": tax.category_of(name), "count": n, "priority": "preferred"}

    years = sorted({int(m.group(1)) for m in _YEARS.finditer(text) if 0 < int(m.group(1)) < 30})
    degrees = sorted({m.group(1) for m in _DEGREE.finditer(text)}, key=str.lower)
    title = next((l.strip() for l in lines if l.strip()), "")[:120]

    return {
        "title_guess": title,
        "skills": sorted(skills.values(), key=lambda s: (s["priority"] != "required", s["category"] == SOFT_CATEGORY, -s["count"], s["name"])),
        "years_mentioned": years,
        "degrees_mentioned": degrees,
        "recurring_terms": recurring_terms(text, exclude=set(skills)),
    }


def recurring_terms(text: str, exclude=(), top=20) -> list:
    """Frequent words/bigrams that are not stopwords or known skills (domain vocabulary)."""
    words = re.findall(r"[A-Za-z][A-Za-z0-9+#.\-]{2,}", text)
    norm = [w.strip(".-").lower() for w in words]
    excl = {e.lower() for e in exclude}
    counts = {}
    for w in norm:
        if w in STOPWORDS or w in excl or len(w) < 3:
            continue
        counts[w] = counts.get(w, 0) + 1
    for a, b in zip(norm, norm[1:]):
        if a in STOPWORDS or b in STOPWORDS or len(a) < 3 or len(b) < 3:
            continue
        k = f"{a} {b}"
        if k in excl:
            continue
        counts[k] = counts.get(k, 0) + 1
    items = [(k, v) for k, v in counts.items() if v >= 2]
    # Prefer bigrams when they are as frequent as their parts.
    items.sort(key=lambda kv: (-kv[1], -len(kv[0].split()), kv[0]))
    return [{"term": k, "count": v} for k, v in items[:top]]


# ----------------------------------------------------------------------------
# Dates
# ----------------------------------------------------------------------------

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
MONTHS_FULL = ["January", "February", "March", "April", "May", "June", "July", "August",
               "September", "October", "November", "December"]
_MONTH_LOOKUP = {m.lower(): i + 1 for i, m in enumerate(MONTHS)}
_MONTH_LOOKUP.update({m.lower(): i + 1 for i, m in enumerate(MONTHS_FULL)})
_MONTH_LOOKUP["sept"] = 9

PRESENT_WORDS = {"present", "current", "now", "ongoing", "today"}


def parse_date(value):
    """Parse ISO-ish or human dates. Returns (year, month|None), 'present', or None."""
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    if s.lower() in PRESENT_WORDS:
        return "present"
    m = re.match(r"^(\d{4})(?:[-/.](\d{1,2}))?(?:[-/.](\d{1,2}))?$", s)
    if m:
        month = int(m.group(2)) if m.group(2) else None
        if month is not None and not 1 <= month <= 12:
            return None
        return (int(m.group(1)), month)
    m = re.match(r"^(\d{1,2})[/.-](\d{4})$", s)
    if m and 1 <= int(m.group(1)) <= 12:
        return (int(m.group(2)), int(m.group(1)))
    m = re.match(r"^([A-Za-z]+)\.?,?\s+(\d{4})$", s)
    if m and m.group(1).lower() in _MONTH_LOOKUP:
        return (int(m.group(2)), _MONTH_LOOKUP[m.group(1).lower()])
    return None


def fmt_date(value, style="mon-yyyy"):
    p = parse_date(value)
    if p is None:
        return str(value or "")
    if p == "present":
        return "Present"
    y, mth = p
    if mth is None or style == "yyyy":
        return str(y)
    if style == "month-yyyy":
        return f"{MONTHS_FULL[mth - 1]} {y}"
    if style == "mm/yyyy":
        return f"{mth:02d}/{y}"
    if style == "yyyy-mm":
        return f"{y}-{mth:02d}"
    return f"{MONTHS[mth - 1]} {y}"


def _is_future(p):
    if not isinstance(p, tuple):
        return False
    today = date.today()
    y, m = p
    return (y, m or 12) > (today.year, today.month)


def fmt_range(start, end, style="mon-yyyy", sep=" – ", open_ended="Present", expected_label=None):
    """Format a date range. `expected_label` (e.g. 'Expected') is used for future end dates."""
    s = fmt_date(start, style) if start else ""
    if end:
        e = fmt_date(end, style)
        if expected_label and _is_future(parse_date(end)):
            e = f"{expected_label} {e}"
    else:
        e = open_ended if start else ""
    if s and e:
        return s if s == e else f"{s}{sep}{e}"
    return s or e


def months_between(start, end=None):
    ps = parse_date(start)
    pe = parse_date(end) if end else "present"
    if not isinstance(ps, tuple):
        return None
    if pe == "present" or pe is None:
        t = date.today()
        pe = (t.year, t.month)
    return (pe[0] - ps[0]) * 12 + ((pe[1] or 12) - (ps[1] or 1))


def iso_to_dt(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def days_ago(iso):
    dt = iso_to_dt(iso)
    if not dt:
        return None
    return (datetime.now(timezone.utc) - dt).days


# ----------------------------------------------------------------------------
# Misc formatting
# ----------------------------------------------------------------------------

def pretty_url(url: str) -> str:
    if not url:
        return ""
    u = re.sub(r"^https?://", "", url.strip(), flags=re.I)
    u = re.sub(r"^www\.", "", u, flags=re.I)
    return u.rstrip("/")


def ensure_url(url: str) -> str:
    if not url:
        return ""
    url = url.strip()
    if re.match(r"^(https?:|mailto:|tel:)", url, re.I):
        return url
    return "https://" + url


def human_count(n) -> str:
    try:
        n = int(n)
    except (TypeError, ValueError):
        return str(n)
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}".rstrip("0").rstrip(".") + "M"
    if n >= 1000:
        return f"{n / 1000:.1f}".rstrip("0").rstrip(".") + "k"
    return str(n)


def log_score(n, scale=1.0):
    return math.log10(max(0, n) + 1) * scale


def slugify(s: str) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "-", s or "").strip("-")
    return s or "cv"


# ----------------------------------------------------------------------------
# Text extraction (what an ATS parser "sees")
# ----------------------------------------------------------------------------

class _HTMLText(HTMLParser):
    BLOCK = {"p", "div", "section", "li", "h1", "h2", "h3", "h4", "h5", "h6", "br", "tr", "header", "ul", "ol", "article"}

    def __init__(self):
        super().__init__()
        self.parts = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("style", "script", "head"):
            self._skip += 1
        if tag in self.BLOCK:
            self.parts.append("\n")
        if tag == "li":
            self.parts.append("• ")

    def handle_endtag(self, tag):
        if tag in ("style", "script", "head"):
            self._skip = max(0, self._skip - 1)
        if tag in self.BLOCK:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self._skip:
            self.parts.append(data)

    def text(self):
        t = "".join(self.parts)
        t = re.sub(r"[ \t]+", " ", t)
        t = re.sub(r"\n\s*\n+", "\n", t)
        return t.strip()


def html_to_text(html: str) -> str:
    p = _HTMLText()
    p.feed(html)
    return p.text()


def docx_to_text(path) -> str:
    """Extract paragraph text from a .docx with the standard library only."""
    ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    import xml.etree.ElementTree as ET
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml")
        names = z.namelist()
    root = ET.fromstring(xml)
    out = []
    for p in root.iter(ns + "p"):
        buf = []
        for run in p.iter(ns + "r"):  # only runs: <w:tab> inside <w:tabs> are tab-stop definitions
            for node in run:
                if node.tag == ns + "t" and node.text:
                    buf.append(node.text)
                elif node.tag == ns + "tab":
                    buf.append("\t")
                elif node.tag in (ns + "br", ns + "cr"):
                    buf.append("\n")
        is_list = p.find(f"{ns}pPr/{ns}numPr") is not None
        style = p.find(f"{ns}pPr/{ns}pStyle")
        if style is not None and "List" in (style.get(ns + "val") or ""):
            is_list = True
        line = "".join(buf)
        out.append(("• " + line) if is_list and line.strip() else line)
    meta = {"has_header_footer_parts": any(n.startswith("word/header") or n.startswith("word/footer") for n in names),
            "has_tables": root.find(f".//{ns}tbl") is not None,
            "has_textboxes": b"txbxContent" in xml,
            "has_images": any(n.startswith("word/media/") for n in names)}
    docx_to_text.last_meta = meta
    return "\n".join(out)


docx_to_text.last_meta = {}


def pdf_to_text(path) -> tuple[str, str]:
    """Return (text, engine). Tries pdfminer.six, pypdf, then pdftotext."""
    errors = []
    try:
        import logging
        logging.getLogger("pdfminer").setLevel(logging.ERROR)
        from pdfminer.high_level import extract_text  # type: ignore
        # some fonts/viewers make pdfminer emit tabs for word gaps; treat them as spaces
        return re.sub(r"[ \t]+", " ", extract_text(str(path))), "pdfminer.six"
    except ImportError:
        errors.append("pdfminer.six not installed")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"pdfminer failed: {exc}")
    try:
        from pypdf import PdfReader  # type: ignore
        reader = PdfReader(str(path))
        text = "\n".join((pg.extract_text() or "") for pg in reader.pages)
        return re.sub(r"[ \t]+", " ", text), "pypdf"  # newer pypdf emits tabs for wide word gaps
    except ImportError:
        errors.append("pypdf not installed")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"pypdf failed: {exc}")
    if shutil.which("pdftotext"):
        res = subprocess.run(["pdftotext", "-layout", str(path), "-"], capture_output=True, text=True)
        if res.returncode == 0:
            return res.stdout, "pdftotext"
        errors.append(res.stderr.strip())
    raise RuntimeError("Could not extract PDF text. Install one of: pip install pdfminer.six pypdf  (" + "; ".join(errors) + ")")


def pdf_page_count(path):
    try:
        from pypdf import PdfReader  # type: ignore
        return len(PdfReader(str(path)).pages)
    except Exception:  # noqa: BLE001
        pass
    if shutil.which("pdfinfo"):
        res = subprocess.run(["pdfinfo", str(path)], capture_output=True, text=True)
        m = re.search(r"^Pages:\s+(\d+)", res.stdout, re.M)
        if m:
            return int(m.group(1))
    return None


def extract_text(path) -> tuple[str, dict]:
    """Extract plain text from pdf/docx/html/md/txt. Returns (text, info)."""
    path = Path(path)
    ext = path.suffix.lower()
    info = {"file": str(path), "type": ext.lstrip(".")}
    if ext == ".pdf":
        text, engine = pdf_to_text(path)
        info["engine"] = engine
        info["pages"] = pdf_page_count(path)
    elif ext == ".docx":
        text = docx_to_text(path)
        info.update(docx_to_text.last_meta)
        info["engine"] = "docx-xml"
    elif ext in (".html", ".htm"):
        text = html_to_text(path.read_text(encoding="utf-8"))
        info["engine"] = "html"
    elif ext in (".txt", ".md", ".markdown"):
        text = path.read_text(encoding="utf-8")
        info["engine"] = "plain"
    else:
        raise ValueError(f"Unsupported file type: {ext}")
    info["bytes"] = path.stat().st_size
    return text, info
