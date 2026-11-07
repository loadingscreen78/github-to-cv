#!/usr/bin/env python3
"""ATS check: score a rendered CV the way a parser and a keyword search would see it.

Usage:
    python ats_check.py Jordan_Lee_Resume.pdf [--jd jd.txt] [--cv cv.json]
                        [--level new-grad|junior|mid|senior|staff|academic]
                        [--out ats-report.md] [--json] [--min-score 80]
    python ats_check.py old_resume.pdf --dump-text      # show exactly what a parser extracts

Works on .pdf, .docx, .html, .md, .txt. With --cv the bullet-level checks read your
cv.json directly (more precise than re-parsing the PDF).

Scoring (100): parseability 25 · contact 10 · sections 15 · JD keywords 30 ·
content quality 15 · length 5. Without a JD the other 70 points are scaled to 100.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (DATA_DIR, SOFT_CATEGORY, extract_text, load_json, months_between,  # noqa: E402
                     parse_date, parse_jd, taxonomy)

SECTION_PATTERNS = {
    "experience": r"(professional |work |relevant |research (?:& |and )?professional |research |industry )?(experience|employment(?: history)?|work history|career history)",
    "education": r"(education|academic background|education (?:& |and )training)",
    "skills": r"((technical |core |key )?skills(?: (?:& |and )\w+)?|core competencies|technologies|tech stack|technical expertise)",
    "projects": r"((selected |personal |academic |key |side )?projects|research software|software (?:& |and )projects)",
    "summary": r"(summary|professional summary|profile|professional profile|about(?: me)?|objective|career objective|research interests)",
    "open source": r"(open[- ]source(?: contributions| software| (?:& |and )community)?)",
    "certifications": r"(certifications?|licen[cs]es? (?:& |and )certifications)",
    "awards": r"(awards|honou?rs(?: (?:& |and )awards)?|achievements)",
    "publications": r"(publications|selected publications)",
}
SECTION_RX = {k: re.compile(r"^\s*" + v + r"\s*:?\s*$", re.I) for k, v in SECTION_PATTERNS.items()}

EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
PHONE = re.compile(r"(?<![\w/])(\+?\d[\d\s().\-]{7,}\d)(?![\w/])")
LINKEDIN = re.compile(r"linkedin\.com/in/[\w\-%.]+", re.I)
GITHUB = re.compile(r"github\.com/[\w\-]+", re.I)
URL = re.compile(r"(https?://|www\.)?[\w\-]+(\.[\w\-]+)+(/[\w\-./%]*)?", re.I)
BULLET_START = re.compile(r"^\s*([•●▪◦‣∙·\-–*]|\d+\.)\s+")
NUMBER = re.compile(r"(\d|%|\$|€|£|₹|\bx\b|×)")
PRONOUN = re.compile(r"\b(I|me|my|mine|we|our|us)\b")
LIGATURES = re.compile("[ﬀ-ﬆ]")
PRIVATE_USE = re.compile("[-�]")
CID = re.compile(r"\(cid:\d+\)")
SPACED = re.compile(r"\b(?:[A-Za-z] ){4,}[A-Za-z]\b")
GENERIC_FILENAME = re.compile(r"^(resume|cv|my[\s_-]?(resume|cv)|untitled|document|final|new)[\s_\-()0-9]*$", re.I)
ACRONYMS = {"AWS": "Amazon Web Services", "GCP": "Google Cloud Platform", "NLP": "Natural Language Processing",
            "Machine Learning": "ML", "CI/CD": "continuous integration", "Infrastructure as Code": "IaC",
            "Site Reliability Engineering": "SRE", "LLMs": "Large Language Models", "RAG": "Retrieval-Augmented Generation",
            "OOP": "Object-Oriented", "TDD": "Test-Driven Development", "ETL": "Extract, Transform, Load"}
LEVEL_PAGES = {"new-grad": (1, 1), "intern": (1, 1), "junior": (1, 1), "mid": (1, 2), "senior": (1, 2),
               "staff": (2, 3), "manager": (2, 3), "academic": (1, 99)}


IRREGULAR = {"led": "lead", "built": "build", "ran": "run", "wrote": "write", "drove": "drive", "grew": "grow", "won": "win",
             "spoke": "speak", "taught": "teach", "sped": "speed", "made": "make", "cut": "cut", "set": "set", "rebuilt": "rebuild",
             "rewrote": "rewrite", "oversaw": "oversee", "brought": "bring", "began": "begin", "sought": "seek", "ran": "run"}
URLISH = re.compile(r"(https?://\S+|www\.\S+|\b[\w.\-]+\.(?:com|io|org|dev|net|ai|app|co|me|uk|in|edu|ac\.uk)/\S*|\S+@\S+)", re.I)


def verb_forms(words):
    """Expand past-tense verbs with present forms so 'Mentor'/'Leads' count in a current role."""
    out = set()
    for w in words:
        w = w.lower()
        out.add(w)
        base = IRREGULAR.get(w)
        if not base and w.endswith("ied"):
            base = w[:-3] + "y"
        elif not base and w.endswith("ed"):
            base = w[:-2]
            if len(base) > 2 and base[-1] == base[-2]:
                out.add(base[:-1])
                out.add(base[:-1] + "s")
            out.add(base + "e")
            out.add(base + "es")
        if base:
            out.add(base)
            out.add(base + "s")
            out.add(base + "es")
    return out


class Report:
    def __init__(self):
        self.items = []

    def add(self, cat, name, earned, maximum, status, detail="", fix=""):
        self.items.append({"category": cat, "check": name, "earned": round(earned, 1), "max": maximum,
                           "status": status, "detail": detail, "fix": fix})

    def total(self, cats=None):
        items = [i for i in self.items if cats is None or i["category"] in cats]
        return sum(i["earned"] for i in items), sum(i["max"] for i in items)


def status_for(ratio):
    return "pass" if ratio >= 0.85 else "warn" if ratio >= 0.5 else "fail"


def detect_headings(lines):
    found = {}
    nonstandard = []
    for i, raw in enumerate(lines):
        s = raw.strip().strip(":").strip()
        if not s or len(s) > 48:
            continue
        for key, rx in SECTION_RX.items():
            if rx.match(s):
                found.setdefault(key, i)
                break
        else:
            if s.isupper() and 1 <= len(s.split()) <= 4 and not EMAIL.search(s) and not re.search(r"\d", s):
                nonstandard.append(s)
    return found, nonstandard


def bullets_from_text(lines):
    out, cur = [], None
    for raw in lines:
        s = raw.strip()
        if not s:
            if cur:
                out.append(cur)
                cur = None
            continue
        m = BULLET_START.match(s)
        if m:
            if cur:
                out.append(cur)
            cur = s[m.end():].strip()
        elif cur and (s[:1].islower() or s[:1].isdigit() or not re.search(r"[.!?;:)]$", cur)) and not any(rx.match(s) for rx in SECTION_RX.values()):
            cur += " " + s
        else:
            if cur:
                out.append(cur)
            cur = None
    if cur:
        out.append(cur)
    return [b for b in out if len(b.split()) >= 3]


def bullets_from_cv(cv, sections=("work", "projects", "openSource", "volunteer")):
    out = []
    for sec in sections:
        for item in cv.get(sec) or []:
            out += [h for h in item.get("highlights") or [] if h]
    for c in cv.get("customSections") or []:
        for e in c.get("entries") or []:
            out += [h for h in e.get("highlights") or [] if h]
    return out


def total_experience_months(cv):
    spans = []
    for w in cv.get("work") or []:
        s, e = parse_date(w.get("startDate")), parse_date(w.get("endDate")) if w.get("endDate") else "present"
        if not isinstance(s, tuple):
            continue
        sm = s[0] * 12 + (s[1] or 1)
        if e == "present" or e is None:
            m = months_between(w.get("startDate"))
            em = sm + (m or 0)
        elif isinstance(e, tuple):
            em = e[0] * 12 + (e[1] or 12)
        else:
            continue
        spans.append((sm, em))
    spans.sort()
    total, cur = 0, None
    for s, e in spans:
        if cur and s <= cur[1]:
            cur = (cur[0], max(cur[1], e))
        else:
            if cur:
                total += cur[1] - cur[0]
            cur = (s, e)
    if cur:
        total += cur[1] - cur[0]
    return total


def check(path, jd_text=None, cv=None, level=None):
    tax = taxonomy()
    verbs = load_json(DATA_DIR / "action_verbs.json")
    strong = verb_forms(v for group in verbs["strong"].values() for v in group)
    weak = {v.lower() for v in verbs["weak"]}
    cliches = verbs["cliches"]
    text, info = extract_text(path)
    lines = [l for l in text.splitlines()]
    nonblank = [l.strip() for l in lines if l.strip()]
    words = re.findall(r"\b\w[\w'+#./-]*\b", text)
    R = Report()

    # --- Parseability (25) ---------------------------------------------------
    if len(words) < 80:
        R.add("parse", "Text layer", 0, 10, "fail", f"Only {len(words)} words extracted.",
              "This looks like an image/scanned file. Export a text-based PDF or DOCX (never a screenshot or Canva image).")
    else:
        R.add("parse", "Text layer", 10, 10, "pass", f"{len(words)} words extracted ({info.get('engine')}).")
    glyph_issues = []
    if LIGATURES.search(text):
        glyph_issues.append("ligature glyphs (ﬁ/ﬂ)")
    if PRIVATE_USE.search(text) or CID.search(text):
        glyph_issues.append("unmapped/icon glyphs")
    spaced = SPACED.findall(text)
    if spaced:
        glyph_issues.append(f"letter-spaced words like “{spaced[0]}”")
    R.add("parse", "Clean characters", 5 if not glyph_issues else 1, 5, "pass" if not glyph_issues else "fail",
          ", ".join(glyph_issues) or "No ligatures, icon fonts or broken glyphs.",
          "Disable ligatures, remove icon fonts/emoji, keep letter-spacing ≤ 0.08em and avoid small-caps." if glyph_issues else "")
    top = "\n".join(nonblank[:6])
    name = (cv or {}).get("basics", {}).get("name") if cv else None
    name_ok = bool(name and name.lower() in top.lower()) if name else bool(nonblank and 1 <= len(nonblank[0].split()) <= 5 and not EMAIL.search(nonblank[0]))
    email_top = bool(EMAIL.search("\n".join(nonblank[:8])))
    ok = name_ok and email_top
    R.add("parse", "Name & contact at the top", 5 if ok else 2 if name_ok else 0, 5, "pass" if ok else "warn",
          "Name and email appear in the first lines." if ok else "Name/email not found in the first lines of extracted text.",
          "" if ok else "Put name and contact details in the document body at the very top — not in a page header/footer, table or text box.")
    hdr_problems = []
    if info.get("has_header_footer_parts"):
        hdr_problems.append("header/footer parts")
    if info.get("has_tables"):
        hdr_problems.append("tables")
    if info.get("has_textboxes"):
        hdr_problems.append("text boxes")
    if info.get("has_images"):
        hdr_problems.append("images")
    R.add("parse", "Layout constructs", 5 if not hdr_problems else 2, 5, "pass" if not hdr_problems else "warn",
          ("DOCX contains " + ", ".join(hdr_problems)) if hdr_problems else "No tables, text boxes, images or header/footer content detected.",
          "Rebuild as a single-column document without tables/text boxes; keep contact info out of headers/footers." if hdr_problems else "")

    # --- Contact (10) ---------------------------------------------------------------
    has_email = bool(EMAIL.search(text))
    has_phone = bool(PHONE.search("\n".join(nonblank[:10])))
    has_link = bool(LINKEDIN.search(text) or GITHUB.search(text))
    R.add("contact", "Email", 4 if has_email else 0, 4, "pass" if has_email else "fail", "",
          "" if has_email else "Add a professional email address.")
    R.add("contact", "Phone", 3 if has_phone else 0, 3, "pass" if has_phone else "warn", "",
          "" if has_phone else "Add a phone number with country code (most ATS forms require it; recruiters call).")
    R.add("contact", "LinkedIn / GitHub URL", 3 if has_link else 0, 3, "pass" if has_link else "warn", "",
          "" if has_link else "Add linkedin.com/in/… and github.com/… as plain-text URLs.")

    # --- Sections (15) ------------------------------------------------------------------
    found, nonstandard = detect_headings(lines)
    student = level in ("new-grad", "intern", "junior") or (cv is not None and not (cv.get("work")))
    exp_ok = "experience" in found or (student and "projects" in found)
    R.add("sections", "Experience section", 5 if exp_ok else 0, 5, "pass" if exp_ok else "fail",
          "Found." if exp_ok else "No recognisable experience heading.",
          "" if exp_ok else "Use a standard heading: “Experience”, “Work Experience” or “Professional Experience”.")
    R.add("sections", "Education section", 4 if "education" in found else 0, 4, "pass" if "education" in found else "fail", "",
          "" if "education" in found else "Add an “Education” section (ATS forms map it to required fields).")
    R.add("sections", "Skills section", 4 if "skills" in found else 0, 4, "pass" if "skills" in found else "warn", "",
          "" if "skills" in found else "Add a “Skills” or “Technical Skills” section — recruiters filter on it.")
    odd = [h for h in nonstandard if h.lower() not in ("present",)][:4]
    R.add("sections", "Standard headings", 2 if not odd else 1, 2, "pass" if not odd else "warn",
          ("Unrecognised headings: " + ", ".join(odd)) if odd else "All headings are standard.",
          "Rename creative headings to standard ones (e.g. “My Journey” → “Experience”)." if odd else "")

    # --- Keywords vs JD (30) ------------------------------------------------------------------
    jd = None
    kw = None
    if jd_text:
        jd = parse_jd(jd_text, tax)
        kw_text = URLISH.sub(" ", text)
        cv_hits = tax.find(kw_text)
        cv_lower = text.lower()
        hard = [s for s in jd["skills"] if s["category"] != SOFT_CATEGORY]
        req = [s for s in hard if s["priority"] == "required"]
        pref = [s for s in hard if s["priority"] == "preferred"]
        def cov(xs):
            return (len([s for s in xs if s["name"] in cv_hits]) / len(xs)) if xs else 1.0
        rq, pf = cov(req), cov(pref)
        R.add("keywords", "Required skills from JD", 22 * rq, 22, status_for(rq),
              f"{int(rq * 100)}% of {len(req)} required hard skills appear.",
              "Add missing required skills you genuinely have — in Skills and inside a bullet that shows them in use.")
        R.add("keywords", "Preferred skills from JD", 8 * pf, 8, status_for(pf),
              f"{int(pf * 100)}% of {len(pref)} preferred skills appear." if pref else "JD lists no preferred skills.", "")
        missing = [s["name"] for s in hard if s["name"] not in cv_hits]
        implied = []
        for m in missing:
            via = [have for have in cv_hits if m in tax.implies.get(have, [])]
            if via:
                implied.append((m, via[0]))
        stuffed = [k for k, v in cv_hits.items() if v >= 10]
        acr = []
        for s in hard:
            n = s["name"]
            if n in ACRONYMS and n in cv_hits and ACRONYMS[n].lower() not in cv_lower:
                acr.append(f"{n} / {ACRONYMS[n]}")
        title = re.split(r"\s+[—–\-|(]\s*|,", jd["title_guess"])[0].strip()
        tw = [w for w in re.findall(r"[A-Za-z+#.]+", title.lower()) if w not in {"and", "of", "the", "a", "to", "for", "in"}]
        head = " ".join(nonblank[:4]).lower()
        title_hit = sum(1 for w in tw if w in head) / len(tw) if tw else 1
        kw = {"required": [{"skill": s["name"], "found": s["name"] in cv_hits} for s in req],
              "preferred": [{"skill": s["name"], "found": s["name"] in cv_hits} for s in pref],
              "soft": [s["name"] for s in jd["skills"] if s["category"] == SOFT_CATEGORY],
              "missing": missing, "implied": implied, "stuffed": stuffed, "acronym_tips": acr,
              "title": title, "title_match": round(title_hit, 2), "years": jd["years_mentioned"],
              "recurring_terms": [t["term"] for t in jd["recurring_terms"][:10]]}

    # --- Content quality (15) ----------------------------------------------------------------------
    bullets = bullets_from_cv(cv) if cv else bullets_from_text(lines)
    if bullets:
        firsts = [re.sub(r"[^A-Za-z\-]", "", b.split()[0]).lower() if b.split() else "" for b in bullets]
        # Role bullets must open with a verb; project/OSS bullets may open with a noun phrase or number.
        verb_pool = bullets_from_cv(cv, ("work", "volunteer")) if cv else bullets
        if not verb_pool:
            verb_pool = bullets
        vfirst = [re.sub(r"[^A-Za-z\-]", "", b.split()[0]).lower() if b.split() else "" for b in verb_pool]
        strong_ratio = sum(1 for f in vfirst if f in strong or (f.endswith("ed") and f not in weak)) / len(verb_pool)
        weak_found = sorted({b.split()[0] for b, f in zip(bullets, firsts) if f in weak})
        quant = sum(1 for b in bullets if NUMBER.search(b)) / len(bullets)
        lens = [len(b.split()) for b in bullets]
        too_long = sum(1 for n in lens if n > 38)
        too_short = sum(1 for n in lens if n < 7)
        R.add("content", "Action-verb openings", 5 * min(1, strong_ratio / 0.9), 5, status_for(strong_ratio / 0.9),
              f"{int(strong_ratio * 100)}% of {len(verb_pool)} role bullets open with a strong verb." + (f" Weak: {', '.join(weak_found[:5])}." if weak_found else ""),
              "Start every bullet with a strong past-tense verb (Built, Cut, Led, Shipped…); drop “Responsible for/Worked on”.")
        R.add("content", "Quantified impact", 5 * min(1, quant / 0.6), 5, status_for(quant / 0.6),
              f"{int(quant * 100)}% of bullets contain a number (aim for 60%+).",
              "Add real numbers: users, latency, %, $, time saved, scale (req/s, rows, stars, downloads). Never invent them.")
        lp = 1 - (too_long + too_short) / len(bullets)
        R.add("content", "Bullet length", 2 * lp, 2, status_for(lp),
              f"{too_long} too long (>38 words), {too_short} too short (<7 words).",
              "Keep bullets to 1–2 lines (~12–30 words).")
        starts = {}
        for f in firsts:
            starts[f] = starts.get(f, 0) + 1
        repeats = [k for k, v in starts.items() if v >= 4 and k]
        if repeats:
            R.items[-1]["detail"] += f" Repeated openers: {', '.join(repeats)}."
    else:
        R.add("content", "Bullets", 0, 12, "warn", "No bullet points detected.",
              "Describe each role/project with 2–5 bullets of achievements, not a paragraph of duties.")
    pron_text = " ".join(bullets) + " " + " ".join(nonblank[:12])
    pron = PRONOUN.findall(pron_text)
    found_cliches = [c for c in cliches if c in text.lower()]
    clean_ok = not pron and not found_cliches
    R.add("content", "No pronouns or clichés", 3 if clean_ok else 1, 3, "pass" if clean_ok else "warn",
          (f"Pronouns: {', '.join(sorted(set(pron)))}. " if pron else "") + (f"Clichés: {', '.join(found_cliches[:5])}." if found_cliches else "") or "Clean.",
          "" if clean_ok else "Write in implied first person (“Built…”, not “I built…”) and replace clichés with evidence.")

    # --- Length (5) -----------------------------------------------------------------------------
    pages = info.get("pages")
    lo, hi = LEVEL_PAGES.get(level or "", (1, 2))
    wc = len(words)
    length_ok = (pages is None or lo <= pages <= hi) and 300 <= wc <= (900 * hi)
    detail = f"{pages} page(s), {wc} words" if pages else f"{wc} words"
    R.add("length", "Length for level", 5 if length_ok else 2, 5, "pass" if length_ok else "warn",
          detail + (f" (target {lo}–{hi} page(s) for {level})" if level else ""),
          "" if length_ok else ("Trim to the target length: cut the weakest bullets/projects first." if (pages and pages > hi) or wc > 900 * hi
                                 else "Add substance: more quantified bullets for projects/experience."))
    fname = Path(path).stem
    tips = []
    if GENERIC_FILENAME.match(fname):
        tips.append(f"Rename the file to First_Last_Resume{Path(path).suffix} — recruiters download hundreds of “{Path(path).name}”.")
    if info.get("bytes", 0) > 2_000_000:
        tips.append("File is over 2 MB; some portals reject large uploads.")
    if cv:
        months = total_experience_months(cv)
        if jd and jd["years_mentioned"] and months is not None:
            need = min(jd["years_mentioned"])
            if months < need * 12 - 6:
                tips.append(f"JD mentions {need}+ years; your listed roles total ~{months // 12} y {months % 12} m. "
                            "Lead with impact and relevant projects/open source; don't inflate dates.")

    # --- Score ---------------------------------------------------------------------------------------
    cats = ["parse", "contact", "sections", "content", "length"] + (["keywords"] if jd else [])
    earned, maximum = R.total(cats)
    score = round(100 * earned / maximum) if maximum else 0
    grade = "Excellent" if score >= 90 else "Strong" if score >= 80 else "Good" if score >= 70 else "Needs work" if score >= 60 else "At risk"
    fixes = sorted([i for i in R.items if i["status"] != "pass" and i["fix"]], key=lambda i: -(i["max"] - i["earned"]))
    return {"file": str(path), "score": score, "grade": grade, "info": info, "checks": R.items, "keywords": kw,
            "top_fixes": [f["fix"] for f in fixes[:6]], "tips": tips, "sections_found": sorted(found),
            "bullets_checked": len(bullets), "source": "cv.json" if cv else "extracted text"}


ICON = {"pass": "✅", "warn": "⚠️", "fail": "❌"}


def to_markdown(r):
    L = [f"# ATS report — {Path(r['file']).name}", "",
         f"**Score: {r['score']}/100 — {r['grade']}**  ", f"Parsed with {r['info'].get('engine')}; "
         f"bullet checks from {r['source']} ({r['bullets_checked']} bullets). Sections found: {', '.join(r['sections_found']) or 'none'}.", ""]
    if r["top_fixes"]:
        L.append("## Top fixes")
        L += [f"{i}. {f}" for i, f in enumerate(r["top_fixes"], 1)]
        L.append("")
    L.append("## Checks")
    L.append("| | Check | Points | Detail |")
    L.append("|---|---|---:|---|")
    for c in r["checks"]:
        L.append(f"| {ICON[c['status']]} | {c['check']} | {c['earned']:g}/{c['max']} | {c['detail']} |")
    kw = r.get("keywords")
    if kw:
        L += ["", "## Job-description keywords"]
        req = ", ".join(("✅ " if k["found"] else "❌ ") + k["skill"] for k in kw["required"]) or "—"
        pref = ", ".join(("✅ " if k["found"] else "❌ ") + k["skill"] for k in kw["preferred"]) or "—"
        L.append(f"**Required:** {req}  ")
        L.append(f"**Preferred:** {pref}")
        if kw["implied"]:
            L.append("")
            L.append("**Exact-term gaps** (a recruiter's keyword search won't infer these):")
            for miss, via in kw["implied"]:
                L.append(f"- JD says **{miss}**; your CV says **{via}** → write “{miss}” explicitly, e.g. “{miss} with {via}”.")
        if kw["acronym_tips"]:
            L.append(f"\nSpell out acronyms once (both forms get searched): {'; '.join(kw['acronym_tips'])}.")
        if kw["title_match"] < 0.6 and kw["title"]:
            L.append(f"\nYour headline doesn't mirror the JD title “{kw['title']}”. If accurate, use it (titles are heavily weighted in ATS ranking).")
        if kw["soft"]:
            L.append(f"\nSoft skills in the JD (prove them in bullets, don't list them): {', '.join(kw['soft'])}.")
        if kw["recurring_terms"]:
            L.append(f"\nDomain terms the JD repeats: {', '.join(kw['recurring_terms'])}.")
        if kw["stuffed"]:
            L.append(f"\n⚠️ Possible keyword stuffing (10+ mentions): {', '.join(kw['stuffed'])}.")
    if r["tips"]:
        L += ["", "## Other tips"] + [f"- {t}" for t in r["tips"]]
    L += ["", "_Only add keywords that are true for you. ATS ranking is a filter for humans, not a replacement — every claim must survive an interview._"]
    return "\n".join(L) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file")
    ap.add_argument("--jd", help="Job description text file")
    ap.add_argument("--cv", help="cv.json used to render the file (more precise bullet checks)")
    ap.add_argument("--level", choices=sorted(LEVEL_PAGES))
    ap.add_argument("--out", help="Write the markdown report here")
    ap.add_argument("--json", action="store_true", help="Print JSON instead of markdown")
    ap.add_argument("--min-score", type=int, help="Exit 1 if the score is below this")
    ap.add_argument("--dump-text", action="store_true", help="Print the extracted text and exit")
    args = ap.parse_args(argv)

    if args.dump_text:
        text, info = extract_text(args.file)
        print(text)
        print(f"\n--- {info} ---", file=sys.stderr)
        return 0
    jd_text = Path(args.jd).read_text(encoding="utf-8") if args.jd else None
    cv = load_json(args.cv) if args.cv else None
    level = args.level or ((cv or {}).get("meta") or {}).get("level")
    r = check(args.file, jd_text=jd_text, cv=cv, level=level)
    md = to_markdown(r)
    if args.out:
        Path(args.out).write_text(md, encoding="utf-8")
    print(json.dumps(r, indent=2, ensure_ascii=False) if args.json else md)
    if args.min_score and r["score"] < args.min_score:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
