#!/usr/bin/env python3
"""Validate a cv.json before rendering: structure, dates, placeholders, writing quality.

Usage:
    python validate_cv.py cv.json [--strict]

Exit code 1 when there are errors (or warnings with --strict).
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import DATA_DIR, SOFT_CATEGORY, TEMPLATES_DIR, load_json, parse_date, taxonomy  # noqa: E402

PLACEHOLDER = re.compile(r"(\bTODO\b|\bTBD\b|\bXXX+\b|lorem|ipsum|\[[^\]]*\]|<[^>]+>|\{\{|\bN/A\b|\?\?\?|\bFIXME\b|example metric|your (name|company))", re.I)
PRONOUN = re.compile(r"\b(I|me|my|we|our)\b")
SECTIONS = ["summary", "skills", "work", "projects", "openSource", "education", "certificates", "awards",
            "publications", "volunteer", "languages", "interests", "references"]
SENSITIVE_US = ["image", "photo", "dateOfBirth", "dob", "birthDate", "age", "gender", "maritalStatus", "nationality", "religion"]


def validate(cv: dict):
    errors, warnings, info = [], [], []
    verbs = load_json(DATA_DIR / "action_verbs.json")
    weak = {v.lower() for v in verbs["weak"]}
    b = cv.get("basics") or {}
    meta = cv.get("meta") or {}

    if not (b.get("name") or "").strip():
        errors.append("basics.name is required.")
    if not (b.get("email") or "").strip():
        errors.append("basics.email is required (every ATS form needs it).")
    elif not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", b["email"]):
        errors.append(f"basics.email looks invalid: {b['email']}")
    if not b.get("phone"):
        warnings.append("basics.phone is empty — most application forms and recruiters expect one.")
    if not b.get("location"):
        warnings.append("basics.location is empty — add at least city and country (ATS filters by location).")
    if not b.get("label"):
        warnings.append("basics.label (headline) is empty — mirror the target job title if accurate.")
    summ = (b.get("summary") or "").strip()
    if summ:
        n = len(summ.split())
        if n > 85:
            warnings.append(f"Summary is {n} words; keep it to 2–4 lines (40–75 words).")
        if PRONOUN.search(summ):
            warnings.append("Summary uses first-person pronouns; write “Backend engineer with…”, not “I am…”.")
    region = (meta.get("region") or "").lower()
    if region in ("us", "ca", "uk", "ie", "au", "nz"):
        bad = [k for k in SENSITIVE_US if b.get(k)]
        if bad:
            warnings.append(f"Remove {', '.join(bad)} for {region.upper()} applications (anti-discrimination norms; photos also hurt parsing).")

    seen_bullets = set()
    numbers = 0
    for sec in ("work", "projects", "openSource", "education", "volunteer", "awards", "certificates", "publications"):
        for i, item in enumerate(cv.get(sec) or []):
            label = f"{sec}[{i}] " + str(item.get("name") or item.get("position") or item.get("institution") or item.get("project") or item.get("title") or "")
            for k in ("startDate", "endDate", "date", "releaseDate"):
                v = item.get(k)
                if v and parse_date(v) is None:
                    errors.append(f"{label}: {k} “{v}” is not a recognised date (use YYYY-MM or YYYY).")
            s, e = parse_date(item.get("startDate")), parse_date(item.get("endDate"))
            if isinstance(s, tuple) and isinstance(e, tuple) and (e[0], e[1] or 12) < (s[0], s[1] or 1):
                errors.append(f"{label}: endDate is before startDate.")
            if sec == "work" and not item.get("position"):
                errors.append(f"{label}: position (job title) is required.")
            if sec == "work" and not item.get("startDate"):
                warnings.append(f"{label}: no startDate — ATS forms require dates for every role.")
            hl = item.get("highlights") or []
            if sec in ("work", "projects") and not hl and not item.get("summary") and not item.get("description"):
                warnings.append(f"{label}: no highlights — add 2–4 achievement bullets.")
            if sec == "work" and len(hl) > 7:
                warnings.append(f"{label}: {len(hl)} bullets; keep the strongest 3–6.")
            for h in hl:
                h = str(h).strip()
                if not h:
                    errors.append(f"{label}: empty highlight.")
                    continue
                if PLACEHOLDER.search(h):
                    errors.append(f"{label}: placeholder text in “{h[:60]}…”.")
                words = h.split()
                if len(words) > 40:
                    warnings.append(f"{label}: bullet is {len(words)} words — split or tighten: “{h[:50]}…”.")
                if words and re.sub(r"[^A-Za-z]", "", words[0]).lower() in weak:
                    warnings.append(f"{label}: weak opener “{words[0]}” — start with an action verb.")
                if PRONOUN.search(h):
                    warnings.append(f"{label}: pronoun in “{h[:50]}…”.")
                if re.search(r"\d", h):
                    numbers += 1
                key = h.lower()
                if key in seen_bullets:
                    warnings.append(f"{label}: duplicate bullet “{h[:50]}…”.")
                seen_bullets.add(key)
            for k in item:
                if k.startswith("_"):
                    info.append(f"{label}: has working key “{k}” (ignored by the renderer; delete when done).")
                    break

    for f in ("name", "label", "summary"):
        if PLACEHOLDER.search(str(b.get(f) or "")):
            errors.append(f"basics.{f} contains placeholder text.")

    if not cv.get("education"):
        warnings.append("No education entries — add them (ATS forms map this section to required fields).")
    if not cv.get("work") and not cv.get("projects"):
        errors.append("Neither work nor projects has entries — a CV needs at least one.")

    tax = taxonomy()
    all_skills = []
    for g in cv.get("skills") or []:
        all_skills += [str(k) for k in g.get("keywords") or []]
    low = [s.lower() for s in all_skills]
    dups = sorted({s for s in all_skills if low.count(s.lower()) > 1})
    if dups:
        warnings.append(f"Skills listed more than once: {', '.join(dups)}.")
    if len(all_skills) > 45:
        warnings.append(f"{len(all_skills)} skills listed — trim to the 20–35 most relevant to the target role.")
    soft = [s for s in all_skills if tax.category_of(tax.canonical(s) or "") == SOFT_CATEGORY]
    if soft:
        warnings.append(f"Soft skills in the skills list ({', '.join(soft)}) — show them in bullets instead.")
    if not all_skills:
        warnings.append("No skills section — recruiters filter on it.")

    tpl = meta.get("template")
    if tpl and not (TEMPLATES_DIR / tpl / "manifest.json").exists():
        errors.append(f"meta.template “{tpl}” does not exist in templates/.")
    customs = {c.get("id") for c in cv.get("customSections") or []}
    for sid in meta.get("sectionOrder") or []:
        if sid not in SECTIONS and sid not in customs:
            errors.append(f"meta.sectionOrder has unknown section “{sid}”.")
    if numbers:
        info.append(f"{numbers} bullets contain numbers — confirm each one came from the user or verifiable data.")
    return errors, warnings, info


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cv")
    ap.add_argument("--strict", action="store_true", help="Treat warnings as errors")
    args = ap.parse_args(argv)
    errors, warnings, info = validate(load_json(args.cv))
    for e in errors:
        print(f"✗ {e}")
    for w in warnings:
        print(f"! {w}")
    for i in info:
        print(f"· {i}")
    if not errors and not warnings:
        print("✓ cv.json looks good.")
    elif not errors:
        print(f"✓ No errors ({len(warnings)} warning(s)).")
    return 1 if errors or (args.strict and warnings) else 0


if __name__ == "__main__":
    sys.exit(main())
