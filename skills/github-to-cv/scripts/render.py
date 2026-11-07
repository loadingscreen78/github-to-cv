#!/usr/bin/env python3
"""Render cv.json into ATS-safe HTML, PDF, DOCX, Markdown and plain text.

Usage:
    python render.py cv.json [--template modern] [--formats pdf,docx,txt]
                     [--out cv-output/<user>] [--paper a4|letter] [--max-pages 1]
                     [--accent "#1f4e79"] [--basename Jordan_Lee_Resume] [--engine auto]
    python render.py --list-templates

Requirements: jinja2 for HTML/PDF; python-docx for DOCX (optional);
a PDF engine — Playwright, any Chrome/Chromium/Edge install, or WeasyPrint.
Markdown and text output need nothing beyond Python.
"""
from __future__ import annotations

import argparse
import copy
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (TEMPLATES_DIR, eprint, ensure_url, fmt_date, fmt_range, load_json,  # noqa: E402
                     pdf_page_count, pretty_url)

DEFAULT_ORDER = ["summary", "skills", "work", "projects", "openSource", "education", "certificates",
                 "awards", "publications", "volunteer", "languages", "interests", "references"]
DEFAULT_TITLES = {
    "summary": "Summary", "skills": "Skills", "work": "Experience", "projects": "Projects",
    "openSource": "Open Source Contributions", "education": "Education", "certificates": "Certifications",
    "awards": "Awards", "publications": "Publications", "volunteer": "Volunteering",
    "languages": "Languages", "interests": "Interests", "references": "References",
}
REGIONS = {
    # paper, document word, date style
    "us": ("letter", "Resume", "mon-yyyy"), "ca": ("letter", "Resume", "mon-yyyy"),
    "in": ("a4", "Resume", "mon-yyyy"), "uk": ("a4", "CV", "mon-yyyy"), "ie": ("a4", "CV", "mon-yyyy"),
    "eu": ("a4", "CV", "mon-yyyy"), "de": ("a4", "CV", "mm/yyyy"), "fr": ("a4", "CV", "mon-yyyy"),
    "nl": ("a4", "CV", "mon-yyyy"), "au": ("a4", "Resume", "mon-yyyy"), "nz": ("a4", "CV", "mon-yyyy"),
    "sg": ("a4", "Resume", "mon-yyyy"), "me": ("a4", "CV", "mon-yyyy"), "apac": ("a4", "Resume", "mon-yyyy"),
    "global": ("a4", "Resume", "mon-yyyy"),
}
PAPER_CSS = {"letter": "8.5in 11in", "a4": "210mm 297mm"}
PAPER_WIDTH = {"letter": "8.5in", "a4": "210mm"}
PAPER_HEIGHT = {"letter": "11in", "a4": "297mm"}
SCALE_STEPS = [1.0, 0.97, 0.94, 0.91, 0.88]


# ----------------------------------------------------------------------------
# Templates
# ----------------------------------------------------------------------------

def list_templates():
    out = []
    for d in sorted(TEMPLATES_DIR.iterdir()):
        if d.is_dir() and not d.name.startswith("_") and (d / "manifest.json").exists():
            m = load_json(d / "manifest.json")
            m["_dir"] = d
            out.append(m)
    return out


def load_manifest(name):
    d = TEMPLATES_DIR / name
    if not (d / "manifest.json").exists():
        names = ", ".join(m["name"] for m in list_templates())
        raise SystemExit(f"Unknown template '{name}'. Available: {names}")
    m = load_json(d / "manifest.json")
    m["_dir"] = d
    return m


# ----------------------------------------------------------------------------
# Context building: cv.json -> plain-text view model shared by every format
# ----------------------------------------------------------------------------

def clean(s):
    return re.sub(r"\s+", " ", str(s)).strip() if s is not None else ""


def location_text(loc):
    if not loc:
        return ""
    if isinstance(loc, str):
        return clean(loc)
    if loc.get("display"):
        return clean(loc["display"])
    parts = [loc.get("city"), loc.get("region"), loc.get("countryCode") or loc.get("country")]
    return ", ".join(clean(p) for p in parts if p)


def build_contacts(basics, meta):
    c = []
    loc = location_text(basics.get("location"))
    if loc:
        c.append({"kind": "location", "text": loc, "url": None})
    if basics.get("phone"):
        c.append({"kind": "phone", "text": clean(basics["phone"]),
                  "url": "tel:" + re.sub(r"[^0-9+]", "", basics["phone"])})
    if basics.get("email"):
        c.append({"kind": "email", "text": clean(basics["email"]), "url": "mailto:" + clean(basics["email"])})
    order = {"linkedin": 0, "github": 1, "gitlab": 2, "portfolio": 3}
    profiles = sorted(basics.get("profiles") or [], key=lambda p: order.get(str(p.get("network", "")).lower(), 9))
    seen = set()
    for p in profiles:
        url = p.get("url") or ""
        if not url and p.get("network", "").lower() == "github" and p.get("username"):
            url = f"https://github.com/{p['username']}"
        if not url or pretty_url(url).lower() in seen:
            continue
        seen.add(pretty_url(url).lower())
        c.append({"kind": str(p.get("network", "link")).lower(), "text": pretty_url(url), "url": ensure_url(url)})
    if basics.get("url") and pretty_url(basics["url"]).lower() not in seen:
        c.append({"kind": "website", "text": pretty_url(basics["url"]), "url": ensure_url(basics["url"])})
    return c


_UNIT_PT = {"in": 72.0, "mm": 72 / 25.4, "cm": 72 / 2.54, "pt": 1.0, "px": 0.75}


def _to_pt(v):
    m = re.match(r"^\s*([\d.]+)\s*(in|mm|cm|pt|px)?\s*$", v or "")
    return float(m.group(1)) * _UNIT_PT[m.group(2) or "pt"] if m else 43.2


def contact_lines(contacts, paper, margins, base_pt):
    """One line if it fits, otherwise details (location/phone/email) and links on two lines.

    Avoids URLs wrapping mid-way and stray '|' at line starts.
    """
    if not contacts:
        return []
    parts = (margins or "").split()
    horiz = parts[1] if len(parts) >= 2 else (parts[0] if parts else "0.6in")
    width = (612 if paper == "letter" else 595.3) - 2 * _to_pt(horiz)
    cpl = width / (base_pt * 0.92 * 0.53)
    one = " | ".join(c["text"] for c in contacts)
    if len(one) <= cpl * 0.97:
        return [contacts]
    personal = [c for c in contacts if c["kind"] in ("location", "phone", "email")]
    links = [c for c in contacts if c not in personal]
    return [l for l in (personal, links) if l]


def degree_text(e):
    st, area = clean(e.get("studyType")), clean(e.get("area"))
    if st and area:
        return f"{st} in {area}" if not re.search(r"\b(in|of)\s*$", st) else f"{st} {area}"
    return st or area


def make_entry(kind, raw, style, ds, sep, opts):
    """Map one cv.json item to a layout-neutral entry with two header rows."""
    e = {"title": "", "extra": "", "extra_sep": "", "link": None, "sub": "", "r1": "", "r2": "",
         "summary": clean(raw.get("summary") or raw.get("description") or ""), "detail": "",
         "highlights": [clean(h) for h in (raw.get("highlights") or []) if clean(h)], "roles": None}
    date = fmt_range(raw.get("startDate"), raw.get("endDate"), ds, sep,
                     expected_label="Expected" if kind == "education" else None)
    loc = location_text(raw.get("location"))
    link_url = raw.get("url") or ""
    if kind in ("work", "volunteer"):
        position = clean(raw.get("position"))
        org = clean(raw.get("name") or raw.get("organization"))
        if style == "org-first":
            e.update(title=org, sub=position, r1=loc, r2=date)
        elif style == "inline":
            e.update(title=position, extra=org + (f" — {loc}" if loc else ""), extra_sep=", ", r1=date)
        else:
            e.update(title=position, sub=org, r1=date, r2=loc)
        if raw.get("_roles"):
            e["roles"] = [{"title": clean(r.get("position")),
                           "date": fmt_range(r.get("startDate"), r.get("endDate"), ds, sep),
                           "summary": clean(r.get("summary")),
                           "highlights": [clean(h) for h in (r.get("highlights") or []) if clean(h)]}
                          for r in raw["_roles"]]
            e.update(title=org, sub="", extra="", r1=loc, r2="", summary="", highlights=[])
    elif kind == "education":
        deg = degree_text(raw)
        details = []
        if raw.get("score"):
            details.append(clean(raw["score"]))
        if raw.get("courses"):
            details.append("Relevant coursework: " + ", ".join(clean(c) for c in raw["courses"]))
        e["detail"] = " · ".join(details)
        if style == "inline":
            e.update(title=deg or clean(raw.get("institution")), extra=clean(raw.get("institution")) if deg else "",
                     extra_sep=", ", r1=date)
        else:
            e.update(title=clean(raw.get("institution")), sub=deg, r1=date, r2=loc)
    elif kind == "projects":
        tech = ", ".join(clean(k) for k in (raw.get("keywords") or []))
        if style == "inline":
            e.update(title=clean(raw.get("name")), extra=tech, extra_sep=" | ")
        else:
            e.update(title=clean(raw.get("name")), sub=tech)
        if opts.get("projectDates", True):
            e["r1"] = date
        if raw.get("homepage") and opts.get("showLinks", True):
            e["link2"] = {"text": pretty_url(raw["homepage"]), "url": ensure_url(raw["homepage"])}
    elif kind == "openSource":
        e.update(title=clean(raw.get("project") or raw.get("name")), sub=clean(raw.get("role")), r1=date)
        if style == "inline" and e["sub"]:
            e.update(extra=e["sub"], extra_sep=" — ", sub="")
    elif kind in ("certificates", "awards"):
        e.update(title=clean(raw.get("name") or raw.get("title")),
                 extra=clean(raw.get("issuer") or raw.get("awarder")), extra_sep=" — ",
                 r1=fmt_date(raw.get("date"), ds) if raw.get("date") else date)
    elif kind == "publications":
        e.update(title=clean(raw.get("name")), extra=clean(raw.get("publisher")), extra_sep=" — ",
                 r1=fmt_date(raw.get("releaseDate"), ds) if raw.get("releaseDate") else "")
        e["citation"] = {
            "authors": author_parts(raw.get("authors"), opts.get("selfName")),
            "title": clean(raw.get("name")), "venue": clean(raw.get("publisher")),
            "year": (fmt_date(raw.get("releaseDate"), "yyyy") if raw.get("releaseDate") else ""),
            "type": clean(raw.get("type")), "note": clean(raw.get("note")),
        }
    elif kind == "references":
        e.update(title=clean(raw.get("name")), summary=clean(raw.get("reference")))
    else:  # custom sections
        e.update(title=clean(raw.get("title") or raw.get("name")), sub=clean(raw.get("subtitle")),
                 r1=clean(raw.get("date")) or date, r2=loc)
        if style == "inline" and e["sub"]:
            e.update(extra=e["sub"], extra_sep=", ", sub="")
    if link_url and opts.get("showLinks", True) and kind in ("projects", "openSource", "publications", "certificates", "custom"):
        e["link"] = {"text": pretty_url(link_url), "url": ensure_url(link_url)}
    e["compact"] = not (e["summary"] or e["highlights"] or e["sub"] or e["r2"] or e["detail"] or e["roles"])
    return e


def author_parts(authors, self_name):
    if not authors:
        return []
    if isinstance(authors, list):
        authors = ", ".join(authors)
    if not self_name:
        return [(authors, False)]
    last = self_name.split()[-1]
    pattern = re.compile(r"(" + re.escape(self_name) + r"|[A-Z]\.(?:\s?[A-Z]\.)*\s" + re.escape(last) + r"|" + re.escape(last) + r",\s[A-Z]\.(?:\s?[A-Z]\.)*)")
    parts, pos = [], 0
    for m in pattern.finditer(authors):
        if m.start() > pos:
            parts.append((authors[pos:m.start()], False))
        parts.append((m.group(0), True))
        pos = m.end()
    if pos < len(authors):
        parts.append((authors[pos:], False))
    return parts


def group_work(items):
    """Merge consecutive roles at the same company into one entry with sub-roles (promotions)."""
    out = []
    for w in items:
        if out and clean(out[-1].get("name")) and clean(out[-1].get("name")) == clean(w.get("name")) and not w.get("_noGroup"):
            prev = out[-1]
            if "_roles" not in prev:
                prev["_roles"] = [copy.deepcopy({k: v for k, v in prev.items() if not k.startswith("_")})]
            prev["_roles"].append(w)
        else:
            out.append(dict(w))
    return out


def build_context(cv, manifest, paper=None, accent=None, scale=1.0, region=None):
    meta = dict(cv.get("meta") or {})
    basics = cv.get("basics") or {}
    region = (region or meta.get("region") or "global").lower()
    r_paper, r_word, r_ds = REGIONS.get(region, REGIONS["global"])
    paper = (paper or meta.get("paper") or r_paper).lower()
    ds = meta.get("dateStyle") or r_ds
    sep = meta.get("dateSeparator") or " – "
    style = meta.get("entryStyle") or manifest.get("entryStyle", "title-first")
    opts = {"showLinks": meta.get("showLinks", True), "projectDates": meta.get("projectDates", manifest.get("projectDates", True)),
            "selfName": clean(basics.get("name"))}
    titles = {**DEFAULT_TITLES, **manifest.get("sectionTitles", {}), **(meta.get("sectionTitles") or {})}
    hidden = set(meta.get("hideSections") or [])
    customs = {c.get("id") or re.sub(r"\W+", "-", c.get("title", "custom")).lower(): c for c in (cv.get("customSections") or [])}
    order = list(meta.get("sectionOrder") or manifest.get("defaultSectionOrder") or DEFAULT_ORDER)
    for sid in DEFAULT_ORDER + list(customs):
        if sid not in order:
            order.append(sid)

    sections = []
    for sid in order:
        if sid in hidden:
            continue
        title = titles.get(sid) or (customs.get(sid) or {}).get("title") or sid.title()
        if sid == "summary":
            if clean(basics.get("summary")):
                sections.append({"id": sid, "kind": "summary", "title": title, "text": clean(basics["summary"])})
        elif sid == "skills":
            groups = [{"name": clean(g.get("name")), "keywords": [clean(k) for k in (g.get("keywords") or []) if clean(k)]}
                      for g in (cv.get("skills") or [])]
            groups = [g for g in groups if g["keywords"] or g["name"]]
            if groups:
                sk = meta.get("skillsStyle") or manifest.get("skillsStyle", "lines")
                flat = [i for g in groups for i in (g["keywords"] or [g["name"]])]
                sections.append({"id": sid, "kind": "skills", "title": title, "groups": groups, "style": sk, "flat": flat})
        elif sid in ("languages", "interests"):
            items = []
            for it in cv.get(sid) or []:
                if sid == "languages":
                    nm, fl = clean(it.get("language")), clean(it.get("fluency"))
                    items.append(f"{nm} ({fl})" if fl else nm)
                else:
                    nm = clean(it.get("name"))
                    kws = ", ".join(clean(k) for k in it.get("keywords") or [])
                    items.append(f"{nm} ({kws})" if kws else nm)
            items = [i for i in items if i]
            if items:
                sections.append({"id": sid, "kind": "inline", "title": title, "elements": items})
        elif sid in customs:
            c = customs[sid]
            entries = [make_entry("custom", x, style, ds, sep, opts) for x in c.get("entries") or []]
            if c.get("items"):
                sections.append({"id": sid, "kind": "inline" if c.get("inline") else "list", "title": title,
                                 "elements": [clean(i) for i in c["items"]]})
            elif entries:
                sections.append({"id": sid, "kind": "entries", "title": title, "entries": entries})
        elif cv.get(sid):
            items = cv[sid]
            if sid == "work":
                items = group_work(items)
            kind = "publications" if sid == "publications" and manifest.get("citationStyle") else "entries"
            entries = [make_entry(sid, x, style, ds, sep, opts) for x in items]
            if entries:
                sections.append({"id": sid, "kind": kind, "title": title, "entries": entries})

    word = meta.get("documentWord") or r_word
    name = clean(basics.get("name")) or "Your Name"
    margins = meta.get("margins") or manifest.get("margins", "0.55in 0.6in")
    base_pt = round(float(meta.get("fontSize") or manifest.get("basePt", 10.5)) * scale, 2)
    contacts = build_contacts(basics, meta)
    css_vars = {"accent": accent or meta.get("accent") or manifest.get("accent", "#1f2937")}
    return {
        "name": name,
        "label": clean(basics.get("label")),
        "contacts": contacts,
        "contact_lines": contact_lines(contacts, paper, margins, base_pt),
        "sections": sections,
        "paper": paper,
        "paper_css": PAPER_CSS.get(paper, PAPER_CSS["a4"]),
        "paper_width": PAPER_WIDTH.get(paper, "210mm"),
        "paper_height": PAPER_HEIGHT.get(paper, "297mm"),
        "margins": margins,
        "base_pt": base_pt,
        "scale": scale,
        "vars": css_vars,
        "doc_word": word,
        "doc_title": f"{name} — {word}",
        "lang": meta.get("language") or "en",
        "keywords": [i for s in sections if s["kind"] == "skills" for i in s["flat"]][:30],
        "manifest": manifest,
        "region": region,
    }


# ----------------------------------------------------------------------------
# HTML
# ----------------------------------------------------------------------------

def render_html(ctx, manifest):
    try:
        import jinja2
    except ImportError:
        raise SystemExit("HTML/PDF output needs Jinja2:  pip install jinja2") from None
    tdir = manifest["_dir"]
    env = jinja2.Environment(loader=jinja2.FileSystemLoader([str(tdir), str(TEMPLATES_DIR / "_base")]),
                             autoescape=jinja2.select_autoescape(["html", "j2"]), trim_blocks=True, lstrip_blocks=True)
    css = (TEMPLATES_DIR / "_base" / "base.css").read_text(encoding="utf-8")
    if (tdir / "style.css").exists():
        css += "\n/* ---- template: " + manifest["name"] + " ---- */\n" + (tdir / "style.css").read_text(encoding="utf-8")
    tpl = env.get_template("template.html.j2" if (tdir / "template.html.j2").exists() else "base.html.j2")
    return tpl.render(cv=ctx, css=css)


# ----------------------------------------------------------------------------
# PDF engines
# ----------------------------------------------------------------------------

def find_chrome():
    env = os.environ.get("CHROME_PATH") or os.environ.get("BROWSER_PATH")
    if env and Path(env).exists():
        return env
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome", "msedge",
                 "microsoft-edge", "microsoft-edge-stable", "brave-browser"):
        p = shutil.which(name)
        if p:
            return p
    candidates = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    ]
    return next((c for c in candidates if c and Path(c).exists()), None)


def pdf_playwright(html_path, pdf_path):
    from playwright.sync_api import sync_playwright  # type: ignore
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except Exception:  # bundled browser not downloaded -> use a system install
            exe = find_chrome()
            if not exe:
                raise
            browser = p.chromium.launch(executable_path=exe)
        page = browser.new_page()
        page.goto(Path(html_path).resolve().as_uri(), wait_until="load")
        page.emulate_media(media="print")
        page.pdf(path=str(pdf_path), prefer_css_page_size=True, print_background=True)
        browser.close()


def pdf_chrome_cli(html_path, pdf_path):
    exe = find_chrome()
    if not exe:
        raise RuntimeError("No Chrome/Chromium/Edge found (set CHROME_PATH)")
    profile = tempfile.mkdtemp(prefix="g2cv-chrome-")
    cmd = [exe, "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
           f"--user-data-dir={profile}", "--no-pdf-header-footer", "--print-to-pdf-no-header",
           f"--print-to-pdf={Path(pdf_path).resolve()}", Path(html_path).resolve().as_uri()]
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        cmd.insert(1, "--no-sandbox")
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
    finally:
        shutil.rmtree(profile, ignore_errors=True)
    if not Path(pdf_path).exists() or Path(pdf_path).stat().st_size == 0:
        raise RuntimeError("Chrome did not produce a PDF: " + (res.stderr or "")[-400:])


def pdf_weasyprint(html_path, pdf_path):
    from weasyprint import HTML  # type: ignore
    HTML(filename=str(html_path)).write_pdf(str(pdf_path))


ENGINES = {"playwright": pdf_playwright, "chrome": pdf_chrome_cli, "weasyprint": pdf_weasyprint}


def make_pdf(html_path, pdf_path, engine="auto"):
    order = [engine] if engine != "auto" else ["playwright", "chrome", "weasyprint"]
    errors = []
    for name in order:
        try:
            ENGINES[name](html_path, pdf_path)
            return name
        except ImportError as exc:
            errors.append(f"{name}: not installed ({exc.name})")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{name}: {str(exc).splitlines()[0][:200] if str(exc) else type(exc).__name__}")
    raise RuntimeError("No PDF engine worked.\n  " + "\n  ".join(errors) +
                       "\nFix: install Google Chrome/Edge, or `pip install playwright && playwright install chromium`, "
                       "or `pip install weasyprint`. Or open the .html file in a browser and Print → Save as PDF "
                       "(margins: none/default, headers & footers off).")


def set_pdf_metadata(pdf_path, ctx):
    try:
        from pypdf import PdfReader, PdfWriter  # type: ignore
    except ImportError:
        return False
    reader = PdfReader(str(pdf_path))
    writer = PdfWriter(clone_from=reader)
    writer.add_metadata({"/Title": ctx["doc_title"], "/Author": ctx["name"], "/Subject": ctx["label"] or ctx["doc_word"],
                         "/Keywords": ", ".join(ctx["keywords"]), "/Creator": "github-to-cv"})
    tmp = Path(str(pdf_path) + ".tmp")
    with open(tmp, "wb") as fh:
        writer.write(fh)
    tmp.replace(pdf_path)
    return True


def last_page_fill(pdf_path):
    """Rough share of text on the last page vs the first (to spot a nearly empty last page)."""
    try:
        from pypdf import PdfReader  # type: ignore
        pages = PdfReader(str(pdf_path)).pages
        if len(pages) < 2:
            return None
        first = len(pages[0].extract_text() or "")
        last = len(pages[-1].extract_text() or "")
        return last / first if first else None
    except Exception:  # noqa: BLE001
        return None


# ----------------------------------------------------------------------------
# DOCX
# ----------------------------------------------------------------------------

def render_docx(ctx, manifest, path):
    try:
        from docx import Document  # type: ignore
        from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT  # type: ignore
        from docx.oxml import OxmlElement  # type: ignore
        from docx.oxml.ns import qn  # type: ignore
        from docx.shared import Inches, Mm, Pt, RGBColor  # type: ignore
    except ImportError:
        raise RuntimeError("DOCX output needs python-docx:  pip install python-docx") from None

    dx = manifest.get("docx", {})
    font = dx.get("font", "Calibri")
    head_font = dx.get("headingFont", font)
    size = float(dx.get("size", 10.5)) * ctx["scale"]
    accent_hex = (ctx["vars"]["accent"] if dx.get("useAccent", True) else "#000000").lstrip("#")
    accent = RGBColor.from_string(accent_hex.upper()[:6].ljust(6, "0"))
    align = WD_ALIGN_PARAGRAPH.CENTER if dx.get("align", "left") == "center" else WD_ALIGN_PARAGRAPH.LEFT

    doc = Document()
    sec = doc.sections[0]
    if ctx["paper"] == "letter":
        sec.page_width, sec.page_height = Inches(8.5), Inches(11)
    else:
        sec.page_width, sec.page_height = Mm(210), Mm(297)
    m = float(dx.get("margin", 0.6))
    sec.left_margin = sec.right_margin = Inches(m)
    sec.top_margin = sec.bottom_margin = Inches(max(0.45, m - 0.1))
    text_width = sec.page_width - sec.left_margin - sec.right_margin

    def set_font(style_or_run, name, sz=None, bold=None, italic=None, color=None):
        f = style_or_run.font
        f.name = name
        if sz:
            f.size = Pt(sz)
        if bold is not None:
            f.bold = bold
        if italic is not None:
            f.italic = italic
        if color is not None:
            f.color.rgb = color
        el = style_or_run.element if hasattr(style_or_run, "element") else style_or_run._element
        rpr = el.get_or_add_rPr()
        rfonts = rpr.find(qn("w:rFonts"))
        if rfonts is None:
            rfonts = OxmlElement("w:rFonts")
            rpr.append(rfonts)
        for attr in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
            rfonts.set(qn(attr), name)

    normal = doc.styles["Normal"]
    set_font(normal, font, size)
    normal.paragraph_format.space_after = Pt(0)
    normal.paragraph_format.space_before = Pt(0)
    normal.paragraph_format.line_spacing = 1.08

    h = doc.styles["Heading 1"]
    set_font(h, head_font, size + 1.5, bold=True, color=accent)
    h.font.all_caps = bool(dx.get("allCapsHeadings", True))
    h.paragraph_format.space_before = Pt(9)
    h.paragraph_format.space_after = Pt(3)
    h.paragraph_format.keep_with_next = True
    ppr = h.element.get_or_add_pPr()
    bdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    for k, v in (("w:val", "single"), ("w:sz", "6"), ("w:space", "1"), ("w:color", accent_hex[:6] if dx.get("ruleAccent", False) else "808080")):
        bottom.set(qn(k), v)
    bdr.append(bottom)
    ppr.append(bdr)

    lb = doc.styles["List Bullet"]
    set_font(lb, font, size)
    lb.paragraph_format.space_after = Pt(1)
    lb.paragraph_format.space_before = Pt(0)

    def para(text="", style=None, align_=None, after=0, before=0):
        p = doc.add_paragraph(style=style)
        if text:
            p.add_run(text)
        if style == "List Bullet":  # direct indent beats the numbering definition's 0.5in default
            p.paragraph_format.left_indent = Inches(0.22)
            p.paragraph_format.first_line_indent = Inches(-0.16)
            after = max(after, 1)
        if align_ is not None:
            p.alignment = align_
        p.paragraph_format.space_after = Pt(after)
        p.paragraph_format.space_before = Pt(before)
        return p

    def head_row(left_runs, right, italic=False, keep=True):
        p = para()
        p.paragraph_format.tab_stops.add_tab_stop(text_width, WD_TAB_ALIGNMENT.RIGHT)
        p.paragraph_format.keep_with_next = keep
        for txt, bold, ital, small in left_runs:
            if not txt:
                continue
            r = p.add_run(txt)
            r.bold = bold
            r.italic = ital or italic
            if small:
                r.font.size = Pt(size - 1)
        if right:
            r = p.add_run("\t" + right)
            r.italic = italic
        return p

    # Header
    p = para(align_=align)
    r = p.add_run(ctx["name"])
    set_font(r, head_font, float(dx.get("nameSize", 22)) * ctx["scale"], bold=True,
             color=accent if dx.get("accentName", False) else None)
    if ctx["label"]:
        p = para(align_=align, before=1)
        r = p.add_run(ctx["label"])
        r.font.size = Pt(size + 1.5)
        if dx.get("accentLabel", True):
            r.font.color.rgb = accent
    for i, line in enumerate(ctx["contact_lines"]):
        last = i == len(ctx["contact_lines"]) - 1
        para(" | ".join(c["text"] for c in line), align_=align, before=3 if i == 0 else 0, after=2 if last else 0)

    for s in ctx["sections"]:
        doc.add_paragraph(s["title"], style="Heading 1")
        if s["kind"] == "summary":
            para(s["text"], after=1)
        elif s["kind"] == "skills":
            if s["style"] == "inline":
                para(" | ".join(s["flat"]), after=1)
            else:
                for g in s["groups"]:
                    p = para(after=1)
                    if g["name"] and g["keywords"]:
                        p.add_run(g["name"] + ": ").bold = True
                        p.add_run(", ".join(g["keywords"]))
                    else:
                        p.add_run(g["name"] or ", ".join(g["keywords"]))
        elif s["kind"] == "inline":
            para(" | ".join(s["elements"]), after=1)
        elif s["kind"] == "list":
            for it in s["elements"]:
                para(it, style="List Bullet")
        else:
            for i, e in enumerate(s["entries"]):
                if s["kind"] == "publications" and e.get("citation"):
                    c = e["citation"]
                    p = para(after=2)
                    p.add_run(f"[{i + 1}] ")
                    for txt, me in c["authors"]:
                        p.add_run(txt).bold = me
                    if c["authors"]:
                        p.add_run(". ")
                    p.add_run(f"“{c['title']}.” ")
                    if c["venue"]:
                        p.add_run(c["venue"]).italic = True
                    if c["year"]:
                        p.add_run(f", {c['year']}")
                    p.add_run(".")
                    if e.get("link"):
                        p.add_run(" " + e["link"]["text"])
                    continue
                left = [(e["title"], True, False, False)]
                if e["extra"]:
                    left.append((e["extra_sep"] + e["extra"], False, False, False))
                if e.get("link"):
                    left.append(("  |  " + e["link"]["text"], False, False, True))
                if e.get("link2"):
                    left.append(("  |  " + e["link2"]["text"], False, False, True))
                has_more = bool(e["sub"] or e["r2"] or e["summary"] or e["highlights"] or e["detail"] or e["roles"])
                p = head_row(left, e["r1"], keep=has_more)
                p.paragraph_format.space_before = Pt(0 if i == 0 else 4)
                if e["sub"] or e["r2"]:
                    head_row([(e["sub"], False, True, False)], e["r2"], italic=True, keep=bool(e["summary"] or e["highlights"]))
                if e["detail"]:
                    para(e["detail"])
                if e["summary"]:
                    para(e["summary"], after=1)
                for hl in e["highlights"]:
                    para(hl, style="List Bullet")
                for role in e["roles"] or []:
                    rp = head_row([(role["title"], False, True, False)], role["date"], italic=True)
                    rp.paragraph_format.space_before = Pt(2)
                    if role["summary"]:
                        para(role["summary"])
                    for hl in role["highlights"]:
                        para(hl, style="List Bullet")

    cp = doc.core_properties
    cp.author = ctx["name"]
    cp.title = ctx["doc_title"]
    cp.subject = ctx["label"] or ctx["doc_word"]
    cp.keywords = ", ".join(ctx["keywords"])
    cp.comments = "Generated with github-to-cv"
    doc.save(str(path))


# ----------------------------------------------------------------------------
# Markdown / plain text
# ----------------------------------------------------------------------------

def _entry_lines(e, md):
    b = (lambda t: f"**{t}**") if md else (lambda t: t)
    it = (lambda t: f"*{t}*") if md else (lambda t: t)
    head = b(e["title"]) + (e["extra_sep"] + e["extra"] if e["extra"] else "")
    bits = [x for x in (e["sub"], e["r2"], e["r1"]) if x]
    line = head + (" — " + " | ".join(bits) if bits else "")
    out = [line]
    links = [l for l in (e.get("link"), e.get("link2")) if l]
    if links:
        out.append(" | ".join((f"[{l['text']}]({l['url']})" if md else l["text"]) for l in links))
    if e["detail"]:
        out.append(it(e["detail"]) if md else e["detail"])
    if e["summary"]:
        out.append(e["summary"])
    out += [f"- {h}" for h in e["highlights"]]
    for r in e["roles"] or []:
        out.append(it(r["title"]) + (" — " + r["date"] if r["date"] else ""))
        if r["summary"]:
            out.append(r["summary"])
        out += [f"- {h}" for h in r["highlights"]]
    return out


def render_text(ctx, md=True):
    L = []
    L.append(f"# {ctx['name']}" if md else ctx["name"].upper())
    if ctx["label"]:
        L.append(f"**{ctx['label']}**" if md else ctx["label"])
    for line in ctx["contact_lines"]:
        L.append(" | ".join(c["text"] for c in line) + ("  " if md and len(ctx["contact_lines"]) > 1 else ""))
    for s in ctx["sections"]:
        L.append("")
        L.append(f"## {s['title']}" if md else s["title"].upper())
        if s["kind"] == "summary":
            L.append(s["text"])
        elif s["kind"] == "skills":
            if s["style"] == "inline":
                L.append(" | ".join(s["flat"]))
            else:
                for g in s["groups"]:
                    nm = (f"**{g['name']}:** " if md else f"{g['name']}: ") if g["name"] and g["keywords"] else ""
                    L.append(nm + ", ".join(g["keywords"] or [g["name"]]))
        elif s["kind"] == "inline":
            L.append(" | ".join(s["elements"]))
        elif s["kind"] == "list":
            L += [f"- {i}" for i in s["elements"]]
        else:
            for i, e in enumerate(s["entries"]):
                if i:
                    L.append("")
                if s["kind"] == "publications" and e.get("citation"):
                    c = e["citation"]
                    auth = "".join((f"**{t}**" if me and md else t) for t, me in c["authors"])
                    L.append(f"{i + 1}. " + (auth + ". " if auth else "") + f"\"{c['title']}.\" " +
                             (f"*{c['venue']}*" if md and c["venue"] else c["venue"]) + (f", {c['year']}" if c["year"] else "") + ".")
                else:
                    L += _entry_lines(e, md)
    return "\n".join(L).strip() + "\n"


# ----------------------------------------------------------------------------

def default_basename(ctx, cv):
    meta = cv.get("meta") or {}
    if meta.get("fileName"):
        return meta["fileName"]
    parts = [re.sub(r"[^A-Za-z0-9\-]", "", p) for p in ctx["name"].split()]
    parts = [p for p in parts if p]
    return "_".join(parts[:3] + [ctx["doc_word"]]) if parts else ctx["doc_word"]


def render_all(cv_path, template=None, formats=("pdf", "docx", "txt"), out_dir=None, paper=None, accent=None,
               basename=None, engine="auto", max_pages=None, region=None, quiet=False):
    cv = load_json(cv_path)
    meta = cv.get("meta") or {}
    template = template or meta.get("template") or "modern"
    manifest = load_manifest(template)
    out_dir = Path(out_dir or Path(cv_path).parent)
    out_dir.mkdir(parents=True, exist_ok=True)
    max_pages = max_pages or meta.get("maxPages")
    formats = [f.strip().lower() for f in formats if f.strip()]
    log = (lambda *a: None) if quiet else print

    ctx = build_context(cv, manifest, paper=paper, accent=accent, region=region)
    base = basename or default_basename(ctx, cv)
    results = {"template": template, "files": {}, "paper": ctx["paper"]}

    need_html = "html" in formats or "pdf" in formats
    html_path = out_dir / f"{base}.html"
    if need_html:
        html_path.write_text(render_html(ctx, manifest), encoding="utf-8")
        if "html" in formats:
            results["files"]["html"] = str(html_path)

    if "pdf" in formats:
        pdf_path = out_dir / f"{base}.pdf"
        used_scale = 1.0
        try:
            engine_used = make_pdf(html_path, pdf_path, engine)
        except RuntimeError as exc:
            # Degrade gracefully: keep the HTML so the user can Print → Save as PDF, and carry on.
            results.setdefault("skipped", {})["pdf"] = str(exc)
            results["files"]["html"] = str(html_path)
            formats = [f for f in formats if f != "pdf"]
            engine_used = None
    if "pdf" in formats and engine_used:
        pages = pdf_page_count(pdf_path)
        if max_pages and pages and pages > max_pages:
            for sc in SCALE_STEPS[1:]:
                ctx = build_context(cv, manifest, paper=paper, accent=accent, scale=sc, region=region)
                html_path.write_text(render_html(ctx, manifest), encoding="utf-8")
                make_pdf(html_path, pdf_path, engine_used)
                pages = pdf_page_count(pdf_path)
                used_scale = sc
                if pages and pages <= max_pages:
                    break
        set_pdf_metadata(pdf_path, ctx)
        results.update(pages=pages, scale=used_scale, engine=engine_used)
        results["files"]["pdf"] = str(pdf_path)
        fill = last_page_fill(pdf_path)
        if max_pages and pages and pages > max_pages:
            results["warning"] = (f"Still {pages} pages at {int(used_scale * 100)}% size (limit {max_pages}). "
                                  "Cut the weakest bullets/projects rather than shrinking further.")
        elif fill is not None and fill < 0.18:
            results["warning"] = (f"Page {pages} is only ~{int(fill * 100)}% full. Trim slightly to fit {pages - 1} "
                                  "page(s), or add substance — a near-empty last page looks unfinished.")
        if "html" not in formats:
            html_path.unlink(missing_ok=True)

    if "docx" in formats:
        p = out_dir / f"{base}.docx"
        try:
            render_docx(ctx, manifest, p)
            results["files"]["docx"] = str(p)
        except RuntimeError as exc:
            results.setdefault("skipped", {})["docx"] = str(exc)
    if "md" in formats or "markdown" in formats:
        p = out_dir / f"{base}.md"
        p.write_text(render_text(ctx, md=True), encoding="utf-8")
        results["files"]["md"] = str(p)
    if "txt" in formats:
        p = out_dir / f"{base}.txt"
        p.write_text(render_text(ctx, md=False), encoding="utf-8")
        results["files"]["txt"] = str(p)

    log(f"✓ Rendered with template '{template}' ({ctx['paper'].upper()})")
    for k, v in results["files"].items():
        extra = ""
        if k == "pdf":
            extra = f"  — {results.get('pages')} page(s), engine: {results.get('engine')}" + \
                    (f", scaled to {int(results['scale'] * 100)}%" if results.get("scale", 1) < 1 else "")
        log(f"  {k:5} {v}{extra}")
    for k, v in (results.get("skipped") or {}).items():
        log(f"  {k:5} skipped: {v}")
    if "pdf" in (results.get("skipped") or {}):
        log(f"  → Open {results['files'].get('html')} in a browser → Print → Save as PDF (headers/footers off).")
    if results.get("warning"):
        log(f"  ! {results['warning']}")
    return results


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cv", nargs="?", help="Path to cv.json")
    ap.add_argument("--template", "-t")
    ap.add_argument("--formats", "-f", default="pdf,docx,txt", help="Comma list of: pdf,docx,html,md,txt (default pdf,docx,txt)")
    ap.add_argument("--out", "-o", help="Output directory (default: next to cv.json)")
    ap.add_argument("--paper", choices=["a4", "letter"])
    ap.add_argument("--region", help="us, ca, uk, ie, eu, de, fr, nl, in, au, nz, sg, me, apac, global")
    ap.add_argument("--accent", help="Accent colour, e.g. '#1f4e79'")
    ap.add_argument("--basename", help="Output file name without extension")
    ap.add_argument("--engine", default="auto", choices=["auto", "playwright", "chrome", "weasyprint"])
    ap.add_argument("--max-pages", type=int, help="Auto-shrink (down to 88%%) to fit this many pages")
    ap.add_argument("--list-templates", action="store_true")
    args = ap.parse_args(argv)

    if args.list_templates:
        for m in list_templates():
            print(f"{m['name']:10} {m.get('displayName', '')} — {m.get('description', '')}")
            print(f"{'':10} best for: {', '.join(m.get('bestFor', []))}")
        return 0
    if not args.cv:
        ap.error("cv.json path required")
    try:
        res = render_all(args.cv, template=args.template, formats=args.formats.split(","), out_dir=args.out,
                         paper=args.paper, accent=args.accent, basename=args.basename, engine=args.engine,
                         max_pages=args.max_pages, region=args.region)
    except RuntimeError as exc:
        eprint(f"✗ {exc}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
