#!/usr/bin/env python3
"""Analyze fetched GitHub data (and optionally a job description) for CV writing.

Usage:
    python analyze_profile.py cv-output/<user>/github.json [--jd jd.txt] [--target "Backend Engineer"]
                              [--out-dir cv-output/<user>] [--top 8]

Writes three files next to the input (or into --out-dir):
    analysis.json   machine-readable results
    analysis.md     human/agent-readable report: ranked projects, skill evidence,
                    JD coverage, questions to ask the user, profile tips
    cv.draft.json   a starter cv.json pre-filled ONLY with facts GitHub can prove
"""
from __future__ import annotations

import argparse
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (SOFT_CATEGORY, days_ago, human_count, load_json, parse_jd,  # noqa: E402
                     pretty_url, save_json, taxonomy)

TUTORIAL = re.compile(r"(tutorial|course|bootcamp|udemy|coursera|freecodecamp|100-?days|exercises?|homework|assignment|"
                      r"hello-?world|my-?first|practice|learning-|learn-|-learning$|crash-?course|workshop)", re.I)
PRACTICE = re.compile(r"(leetcode|hackerrank|codewars|codeforces|kata|dsa|interview-?prep|advent-?of-?code|aoc-?\d{2,4})", re.I)
STARTER = re.compile(r"(^|[-_])(todo|to-do|calculator|weather-?app|tic-?tac-?toe|clone|demo|test|sample|starter|boilerplate|template)([-_]|$)", re.I)
META = re.compile(r"(^dotfiles$|^\.github$|^config$|^dots$)", re.I)
METRIC = re.compile(r"\b\d[\d,.]*\s*(?:%|x\b|×|ms\b|µs|us\b|sec\b|seconds|minutes|hours|req/s|rps|qps|ops/s(?:ec)?|tps|"
                    r"users|downloads|installs|stars|customers|teams|companies|MB\b|GB\b|TB\b|requests|transactions|"
                    r"transfers|events|messages|records|rows|faster|slower|reduction|accuracy|F1|precision|recall)", re.I)
PKG_PATTERNS = [
    ("PyPI", re.compile(r"pypi\.org/project/([A-Za-z0-9_.\-]+)", re.I)),
    ("PyPI", re.compile(r"pip3? install\s+(?:-U\s+)?([A-Za-z0-9_.\-]+)", re.I)),
    ("npm", re.compile(r"npmjs\.com/package/((?:@[\w.\-]+/)?[\w.\-]+)", re.I)),
    ("npm", re.compile(r"(?:npm (?:i|install)|yarn add|pnpm add)\s+(?:-[DSg]\s+)?((?:@[\w.\-]+/)?[\w.\-]+)", re.I)),
    ("crates.io", re.compile(r"crates\.io/crates/([\w\-]+)", re.I)),
    ("Docker Hub", re.compile(r"hub\.docker\.com/r/([\w\-]+/[\w\-]+)", re.I)),
    ("Go module", re.compile(r"go (?:get|install)\s+(github\.com/[\w.\-/]+)", re.I)),
]


def readme_facts(text: str):
    """Pull lines that contain measurable claims, and published package names."""
    if not text:
        return [], []
    facts = []
    plain = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
    plain = re.sub(r"</?[A-Za-z][^>\n]*(?:>|$)", " ", plain, flags=re.M)  # drop HTML tags (img/td/sub...)
    for raw in re.split(r"(?<=[.!?])\s+|\n", plain):
        line = re.sub(r"!\[[^\]]*\]\([^)]*\)|\[([^\]]*)\]\([^)]*\)|[*_`#>|]", lambda m: m.group(1) or "", raw).strip(" -")
        if 12 <= len(line) <= 220 and METRIC.search(line) and not re.search(r"(version|v\d+\.\d+|python\s*3\.\d|node\s*\d|license|copyright|©)", line, re.I):
            facts.append(line)
        if len(facts) >= 5:
            break
    pkgs = []
    for registry, rx in PKG_PATTERNS:
        for m in rx.finditer(text):
            name = m.group(1).rstrip(".,)")
            if not re.match(r"[A-Za-z0-9@]", name):
                continue
            if name.lower() in {"-r", "requirements.txt", "-e", ".", "pip", "poetry", "--upgrade", "-u"}:
                continue
            if (registry, name) not in pkgs:
                pkgs.append((registry, name))
    stats = {"PyPI": "https://pypistats.org/packages/{}", "npm": "https://www.npmjs.com/package/{}",
             "crates.io": "https://crates.io/crates/{}", "Docker Hub": "https://hub.docker.com/r/{}",
             "Go module": "https://pkg.go.dev/{}?tab=importedby"}
    return facts, [{"registry": r, "name": n, "stats_url": stats[r].format(n.lower() if r == "PyPI" else n)} for r, n in pkgs[:4]]

ACRONYMS = {"api", "cli", "ui", "ux", "db", "kv", "ml", "ai", "llm", "sdk", "http", "sql", "css", "html", "js", "ts", "rpc",
            "aws", "gcp", "iot", "nlp", "os", "vm", "gpu", "cpu", "rest", "jwt", "etl", "ci", "cd", "pdf", "csv", "json",
            "yaml", "url", "dns", "tcp", "udp", "p2p", "ar", "vr", "3d", "2d", "mvp", "crm", "erp", "seo", "rag", "ocr",
            "gan", "cnn", "rnn", "nft", "dao", "ide", "orm", "mqtt", "ble", "rtos", "fpga", "gui", "tui", "id", "qr", "pg", "k8s"}

CV_CATEGORY = {
    "Languages": "Languages", "Frontend": "Frontend", "Backend": "Backend", "Databases": "Databases",
    "Cloud": "Cloud & DevOps", "DevOps": "Cloud & DevOps", "Data & ML": "Data & ML", "Mobile": "Mobile",
    "Testing": "Testing", "Security": "Security", "Embedded & Hardware": "Embedded & Hardware",
    "Game Development": "Game Development", "Web3": "Web3", "Tools": "Tools", "Practices": "Practices",
}
TRIVIAL_SKILLS = {"Git", "GitHub", "VS Code", "npm", "Yarn", "pnpm", "Version Control", "Technical Documentation",
                  "Caching", "Performance Optimization", "Open Source", "Observability"}


def pretty_name(repo_name: str) -> str:
    tax = taxonomy()
    def exact(w):  # only respell exact canonical names (fastapi -> FastAPI), never aliases (k8s stays k8s)
        e = tax.by_name.get(w.lower())
        return e["name"] if e and len(w) > 1 else None
    if not re.search(r"[-_.]", repo_name):
        return exact(repo_name) or (repo_name[0].upper() + repo_name[1:] if repo_name.islower() else repo_name)
    words = [w for w in re.split(r"[-_.]+", repo_name) if w]
    out = []
    for w in words:
        canon = exact(w)
        if w.lower() == "k8s":
            out.append("K8s")
        elif canon:
            out.append(canon)
        elif w.lower() in ACRONYMS:
            out.append(w.upper())
        elif w.islower():
            out.append(w.capitalize())
        else:
            out.append(w)
    return " ".join(out)


def repo_flags(r, login):
    name = r["name"]
    flags = []
    if name.lower() == login.lower():
        flags.append("profile-readme")
    if name.lower() in (f"{login.lower()}.github.io",):
        flags.append("personal-site")
    if META.search(name):
        flags.append("config")
    if TUTORIAL.search(name) or TUTORIAL.search(r.get("description") or ""):
        flags.append("tutorial-like")
    if PRACTICE.search(name):
        flags.append("practice")
    if STARTER.search(name) and (r.get("stargazers_count") or 0) < 5:
        flags.append("starter-project")
    if r.get("archived"):
        flags.append("archived")
    if not r.get("description"):
        flags.append("no-description")
    if r.get("deep") and (r.get("readme_length") or 0) < 300:
        flags.append("thin-readme")
    if r.get("fork"):
        flags.append("fork")
    return flags


def repo_skills(r, tax, flags=()):
    """Return {skill: strength} where strength is 3 strong / 2 medium / 1 weak.

    Tutorial/starter/practice repos only ever produce weak evidence, and implied
    skills (Terraform -> Infrastructure as Code) are capped at medium.
    """
    found = {}

    def bump(name, s):
        if name and name not in found or (name and found[name] < s):
            found[name] = s

    langs = r.get("languages") or {}
    total = sum(langs.values()) or 0
    if langs:
        for lang, b in langs.items():
            canon = tax.map_github_language(lang)
            if not canon:
                continue
            share = b / total if total else 0
            bump(canon, 3 if share >= 0.10 else 2 if share >= 0.02 else 1)
    elif r.get("language"):
        bump(tax.map_github_language(r["language"]), 3)
    for t in r.get("topics") or []:
        for s in tax.find(t.replace("-", " ")):
            bump(s, 3)
    for s in tax.find(" ".join([re.sub(r"[-_.]+", " ", r["name"]), r.get("description") or ""])):
        bump(s, 2)
    for s in tax.find(r.get("readme") or ""):
        bump(s, 1)
    for s, k in list(found.items()):
        for t in tax.implies.get(s, []):
            bump(t, min(k, 2))
    if {"tutorial-like", "starter-project", "practice"} & set(flags):
        found = {k: 1 for k in found}
    return found


def score_repo(r, flags, skills, jd_skills, target_skills):
    reasons = []
    stars, forks = r.get("stargazers_count") or 0, r.get("forks_count") or 0
    pop = min(40.0, math.log10(stars + 1) * 20 + math.log10(forks + 1) * 10)
    if stars or forks:
        reasons.append(f"{stars}★/{forks} forks")
    age = days_ago(r.get("pushed_at"))
    rec = 15 if age is not None and age < 180 else 10 if age is not None and age < 365 else 5 if age is not None and age < 730 else 0
    if rec >= 10:
        reasons.append("recently active")
    doc = 0
    rl = r.get("readme_length") or 0
    if r.get("deep"):
        doc += 10 if rl > 1500 else 6 if rl > 400 else 0
        if rl > 1500:
            reasons.append("solid README")
    doc += 4 if r.get("description") else 0
    doc += 4 if r.get("homepage") else 0
    doc += min(4, len(r.get("topics") or []))
    if r.get("homepage"):
        reasons.append("live demo/homepage")
    size = r.get("size") or 0
    subst = 6 if size > 500 else 4 if size > 100 else 2 if size > 20 else 0
    rel = 0
    if jd_skills or target_skills:
        hits = []
        for s, strength in skills.items():
            if strength < 2:
                continue
            if s in jd_skills:
                rel += 2 if jd_skills[s]["priority"] == "required" else 1
                hits.append(s)
            elif s in target_skills:
                rel += 1
                hits.append(s)
        rel = min(25, rel * 5)
        if hits:
            reasons.append("matches JD: " + ", ".join(sorted(hits)[:5]))
    penalty = 0
    for f, p in (("tutorial-like", 20), ("practice", 10), ("starter-project", 10), ("archived", 5),
                 ("config", 40), ("profile-readme", 60), ("fork", 25)):
        if f in flags:
            penalty += p
    total = max(0.0, min(100.0, pop + rec + doc + subst + rel - penalty))
    return round(total, 1), reasons


def analyze(gh: dict, jd_text: str | None = None, target: str | None = None, top: int = 8) -> dict:
    tax = taxonomy()
    profile = gh["profile"]
    login = profile["login"]
    repos = gh.get("repos", [])
    jd = parse_jd(jd_text, tax) if jd_text else None
    jd_skills = {s["name"]: s for s in (jd["skills"] if jd else [])}
    target_skills = tax.find(target) if target else {}

    # Languages ---------------------------------------------------------------
    lang_bytes, lang_repos = {}, {}
    own = [r for r in repos if not r.get("fork")]
    for r in own:
        langs = r.get("languages") or ({r["language"]: 0} if r.get("language") else {})
        for lang, b in langs.items():
            if lang in tax.noise_languages:
                continue
            canon = "Jupyter Notebook" if lang == "Jupyter Notebook" else tax.map_github_language(lang)
            if not canon or tax.category_of(canon) not in ("Languages", "Frontend", None):
                continue
            lang_bytes[canon] = lang_bytes.get(canon, 0) + (b or 0)
            lang_repos.setdefault(canon, set()).add(r["name"])
    total_bytes = sum(lang_bytes.values()) or 1
    languages = sorted(({"name": k, "bytes": v, "share": round(100 * v / total_bytes, 1), "repos": len(lang_repos[k])}
                        for k, v in lang_bytes.items()), key=lambda x: (-x["bytes"], -x["repos"]))

    # Projects ----------------------------------------------------------------
    projects = []
    evidence = {}
    for r in repos:
        flags = repo_flags(r, login)
        skills = repo_skills(r, tax, flags)
        score, reasons = score_repo(r, flags, skills, jd_skills, target_skills)
        facts, packages = readme_facts(r.get("readme") or "")
        projects.append({
            "name": r["name"], "display_name": pretty_name(r["name"]), "full_name": r["full_name"],
            "url": r["html_url"], "homepage": r.get("homepage") or None, "description": r.get("description"),
            "stars": r.get("stargazers_count") or 0, "forks": r.get("forks_count") or 0,
            "language": r.get("language"), "topics": r.get("topics") or [], "pinned": r.get("pinned", False),
            "created": (r.get("created_at") or "")[:10], "pushed": (r.get("pushed_at") or "")[:10],
            "fork": r.get("fork", False), "deep": r.get("deep", False), "score": score, "reasons": reasons,
            "flags": flags, "skills": dict(sorted(skills.items(), key=lambda kv: (-kv[1], kv[0]))),
            "readme_facts": facts, "packages": packages,
        })
        if r.get("fork") or {"profile-readme", "config"} & set(flags):
            continue
        weight = 1 + score / 25
        for s, strength in skills.items():
            ev = evidence.setdefault(s, {"name": s, "category": tax.category_of(s) or "Languages", "strength": 0,
                                         "weight": 0.0, "repos": []})
            ev["strength"] = max(ev["strength"], strength)
            ev["weight"] += weight * strength
            ev["repos"].append(r["name"])
    # Pinned repos get a boost; the user chose them.
    for p in projects:
        if p["pinned"]:
            p["score"] = min(100.0, p["score"] + 10)
            p["reasons"].append("pinned on profile")
    projects.sort(key=lambda p: -p["score"])
    excluded = {"profile-readme", "config", "personal-site", "tutorial-like", "starter-project", "practice"}
    featured = [p for p in projects if not p["fork"] and not excluded & set(p["flags"]) and p["score"] >= 20][:top]

    skills_list = sorted(evidence.values(), key=lambda e: (-e["strength"], -e["weight"], e["name"]))
    for e in skills_list:
        e["weight"] = round(e["weight"], 1)
        e["level"] = {3: "strong", 2: "medium", 1: "weak"}[e["strength"]]
        e["repos"] = sorted(set(e["repos"]))

    # Open source ---------------------------------------------------------------
    ext = []
    for g in gh.get("external_contributions", []):
        ext.append({k: g.get(k) for k in ("full_name", "url", "merged_prs", "stars", "description", "language",
                                           "titles", "pr_urls", "first", "last", "owner_is_user_org")})
    ext.sort(key=lambda g: (-(math.log10((g.get("stars") or 0) + 1) * 2 + (g.get("merged_prs") or 0))))
    real_oss = [g for g in ext if not g.get("owner_is_user_org")]
    if real_oss:
        oss_ev = {"name": "Open Source", "category": "Practices", "strength": 3, "level": "strong",
                  "weight": float(sum(g.get("merged_prs") or 0 for g in real_oss)),
                  "repos": [g["full_name"] for g in real_oss]}
        if "Open Source" in evidence:
            skills_list.remove(evidence["Open Source"])
        evidence["Open Source"] = oss_ev
        skills_list.insert(0, oss_ev)

    # Activity --------------------------------------------------------------------
    created_days = days_ago(profile.get("created_at")) or 0
    own_real = [p for p in projects if not p["fork"] and not {"profile-readme", "config"} & set(p["flags"])]
    activity = {
        "account_years": round(created_days / 365.25, 1),
        "own_repos": len(own_real),
        "forks": len([p for p in projects if p["fork"]]),
        "total_stars": sum(p["stars"] for p in own_real),
        "total_forks": sum(p["forks"] for p in own_real),
        "repos_10_plus_stars": len([p for p in own_real if p["stars"] >= 10]),
        "repos_pushed_last_year": len([p for p in own_real if (days_ago(p["pushed"] + "T00:00:00+00:00") or 9999) < 365]),
        "followers": profile.get("followers"),
        "external_projects": len(ext),
        "external_merged_prs": sum(g.get("merged_prs") or 0 for g in ext),
        "contributions_last_year": gh.get("contributions_last_year"),
    }

    # JD coverage ---------------------------------------------------------------
    coverage = None
    if jd:
        rows = []
        for s in jd["skills"]:
            ev = evidence.get(s["name"])
            rows.append({**s, "evidence": ev["level"] if ev else "none", "repos": (ev or {}).get("repos", [])[:5]})
        hard = [r for r in rows if r["category"] != SOFT_CATEGORY]
        req = [r for r in hard if r["priority"] == "required"]
        pref = [r for r in hard if r["priority"] == "preferred"]

        def pct(xs, levels=("strong", "medium")):
            return round(100 * len([x for x in xs if x["evidence"] in levels]) / len(xs)) if xs else None
        coverage = {"rows": rows, "required_pct": pct(req), "preferred_pct": pct(pref),
                    "required_missing": [r["name"] for r in req if r["evidence"] in ("none", "weak")],
                    "preferred_missing": [r["name"] for r in pref if r["evidence"] in ("none", "weak")],
                    "soft_skills": [r["name"] for r in rows if r["category"] == SOFT_CATEGORY]}

    # Questions for the user -------------------------------------------------------
    questions = []
    for i, p in enumerate(featured[:5]):
        if i == 0:
            q = (f"**{p['display_name']}** ({pretty_url(p['url'])}): what problem does it solve and for whom? Any numbers — "
                 "users, downloads, latency/accuracy/cost gains, time saved? Solo or team (your role)?")
        else:
            q = f"**{p['display_name']}**: same questions — who uses it, any numbers, your role?"
        if not p["homepage"]:
            q += " Live URL?"
        if p["packages"]:
            q += " Published as " + ", ".join(f"`{x['name']}` ({x['registry']})" for x in p["packages"][:2]) + " — check the stats link and confirm."
        questions.append(q)
    if coverage:
        for name in coverage["required_missing"][:8]:
            ev = evidence.get(name)
            if ev:
                questions.append(f"The JD requires **{name}**; GitHub only mentions it in passing ({', '.join(ev['repos'][:3])}). Did you use it substantially? Where?")
            else:
                questions.append(f"The JD requires **{name}** and GitHub shows no evidence. Have you used it at work, school or elsewhere? (Only include it if yes.)")
    if not profile.get("email"):
        questions.append("What email and phone should appear on the CV? (GitHub email is private.)")
    socials = {(s.get("provider") or "").lower(): s.get("url") for s in gh.get("social_accounts", [])}
    if "linkedin" not in socials:
        questions.append("LinkedIn profile URL (recommended for every region)?")

    # Profile tips ------------------------------------------------------------------
    tips = []
    if not profile.get("name"):
        tips.append("Add your real name to your GitHub profile — recruiters cross-check the CV against it.")
    if not profile.get("bio"):
        tips.append("Add a one-line bio matching your CV headline (e.g. 'Backend engineer · Python, Go, AWS').")
    if not gh.get("profile_readme"):
        tips.append(f"Create a profile README (a repo named `{login}`) with a 3-line intro and links to your best work.")
    if gh.get("authenticated") and not gh.get("pinned"):
        tips.append("Pin your 4–6 best repositories so they show first on your profile.")
    for p in featured[:6]:
        miss = [f for f in ("no-description", "thin-readme") if f in p["flags"]]
        if not p["topics"]:
            miss.append("no topics")
        if miss:
            tips.append(f"`{p['name']}`: fix {', '.join(m.replace('-', ' ') for m in miss)} — it is a CV project, so recruiters will open it.")

    personal_site = profile.get("blog") or next((f"https://{login}.github.io" for p in projects if "personal-site" in p["flags"]), None)

    return {
        "schema": "github-to-cv/analysis@1",
        "login": login,
        "profile": profile,
        "socials": socials,
        "personal_site": personal_site,
        "languages": languages,
        "skills": skills_list,
        "projects": projects,
        "featured": [p["name"] for p in featured],
        "open_source": ext,
        "activity": activity,
        "jd": jd,
        "jd_coverage": coverage,
        "questions": questions,
        "profile_tips": tips,
        "orgs": gh.get("orgs", []),
        "warnings": gh.get("warnings", []),
    }


# ----------------------------------------------------------------------------

def to_markdown(a: dict) -> str:
    p = a["profile"]
    act = a["activity"]
    L = []
    L.append(f"# GitHub analysis — @{a['login']}\n")
    L.append(f"**{p.get('name') or a['login']}** · {p.get('bio') or '_no bio_'} · {p.get('location') or '_no location_'}")
    L.append(f"Account age {act['account_years']} y · {act['own_repos']} own repos · {act['total_stars']} stars earned · "
             f"{act['repos_10_plus_stars']} repos with 10+ stars · {act['external_merged_prs']} merged PRs to "
             f"{act['external_projects']} other projects · {p.get('followers', 0)} followers")
    if act.get("contributions_last_year"):
        c = act["contributions_last_year"]
        L.append(f"Last 12 months: {c.get('total')} contributions ({c.get('commits')} commits, {c.get('pull_requests')} PRs, {c.get('reviews')} reviews)")
    if a.get("warnings"):
        L.append("\n> Fetch warnings: " + "; ".join(a["warnings"][:5]))

    L.append("\n## Top languages (by bytes in own repos)\n")
    for l in a["languages"][:10]:
        share = f"{l['share']}%" if l["bytes"] else "share n/a (not deep-fetched)"
        L.append(f"- {l['name']}: {share} · {l['repos']} repo{'s' if l['repos'] != 1 else ''}")

    L.append("\n## Ranked projects\n")
    L.append("| # | Repo | Score | ★ | Lang | Why | Flags |")
    L.append("|---|------|------:|--:|------|-----|-------|")
    for i, pr in enumerate([x for x in a["projects"] if not x["fork"]][:15], 1):
        star = " ⭐featured" if pr["name"] in a["featured"] else ""
        L.append(f"| {i} | [{pr['name']}]({pr['url']}){star} | {pr['score']} | {pr['stars']} | {pr['language'] or ''} | "
                 f"{'; '.join(pr['reasons']) or '—'} | {', '.join(pr['flags']) or ''} |")

    facts = [(x, f) for x in a["projects"] if x["name"] in a["featured"] for f in x.get("readme_facts", [])]
    pkgs = [(x, k) for x in a["projects"] if x["name"] in a["featured"] for k in x.get("packages", [])]
    if facts or pkgs:
        L.append("\n## Measurable claims found in READMEs (verify before using)\n")
        for x, f in facts[:15]:
            L.append(f"- `{x['name']}`: {f}")
        for x, k in pkgs:
            L.append(f"- `{x['name']}` is published on {k['registry']} as `{k['name']}` — usage stats: {k['stats_url']} (strong bullet metric if notable).")

    L.append("\n## Skill evidence\n")
    L.append("_strong_ = language share ≥10% or repo topic · _medium_ = in name/description or minor language · "
             "_weak_ = only mentioned in a README (confirm with the user before claiming).\n")
    for level in ("strong", "medium", "weak"):
        items = [s for s in a["skills"] if s["level"] == level and s["category"] != SOFT_CATEGORY and s["name"] not in TRIVIAL_SKILLS]
        if items:
            L.append(f"**{level.title()}:** " + ", ".join(f"{s['name']} ({len(s['repos'])})" for s in items[:40]))

    if a["open_source"]:
        L.append("\n## Open-source contributions (merged PRs to others' repos)\n")
        for g in a["open_source"][:10]:
            stars = f"{human_count(g['stars'])} stars" if g.get("stars") is not None else "stars unknown"
            org = " (your org)" if g.get("owner_is_user_org") else ""
            L.append(f"- [{g['full_name']}]({g['url']}){org} — {g['merged_prs']} merged PR(s), {stars}. "
                     f"e.g. “{(g.get('titles') or [''])[0]}”")

    cov = a.get("jd_coverage")
    if cov:
        jd = a["jd"]
        L.append(f"\n## Job description match — “{jd['title_guess']}”\n")
        L.append(f"Required hard skills with GitHub evidence: **{cov['required_pct']}%** · Preferred: **{cov['preferred_pct']}%**")
        if jd.get("years_mentioned"):
            L.append(f"Years of experience mentioned: {', '.join(map(str, jd['years_mentioned']))}")
        L.append("\n| Skill | Priority | Evidence | Where |")
        L.append("|---|---|---|---|")
        for r in cov["rows"]:
            if r["category"] == SOFT_CATEGORY:
                continue
            L.append(f"| {r['name']} | {r['priority']} | {r['evidence']} | {', '.join(r['repos'][:3])} |")
        if cov["soft_skills"]:
            L.append(f"\nSoft skills the JD asks for (show through bullets, not the skills list): {', '.join(cov['soft_skills'])}")
        if jd.get("recurring_terms"):
            L.append("Recurring domain terms (mirror where true): " + ", ".join(t["term"] for t in jd["recurring_terms"][:12]))

    L.append("\n## Questions to ask the user\n")
    for q in a["questions"]:
        L.append(f"- {q}")
    if a["profile_tips"]:
        L.append("\n## GitHub profile tips (optional, share with the user)\n")
        for t in a["profile_tips"]:
            L.append(f"- {t}")
    L.append("\n---\nRules: claim only what the data or the user confirms. Weak evidence ≠ skill. Never invent metrics.")
    return "\n".join(L) + "\n"


def draft_cv(a: dict, target: str | None = None) -> dict:
    p = a["profile"]
    tax = taxonomy()
    profiles = [{"network": "GitHub", "username": a["login"], "url": p.get("html_url") or f"https://github.com/{a['login']}"}]
    for prov, url in a.get("socials", {}).items():
        if prov == "linkedin":
            profiles.insert(0, {"network": "LinkedIn", "username": "", "url": url})
    projects = []
    by_name = {x["name"]: x for x in a["projects"]}
    for name in a["featured"][:5]:
        pr = by_name[name]
        kw = [s for s, strength in pr["skills"].items() if strength >= 2 and s not in TRIVIAL_SKILLS
              and tax.category_of(s) != SOFT_CATEGORY][:6]
        recent = (days_ago(pr["pushed"] + "T00:00:00+00:00") or 9999) < 120
        projects.append({
            "name": pr["display_name"],
            "description": pr["description"] or "",
            "url": pr["url"],
            **({"homepage": pr["homepage"]} if pr["homepage"] else {}),
            "keywords": kw,
            "startDate": pr["created"][:7],
            **({} if recent else {"endDate": pr["pushed"][:7]}),
            "highlights": [],
            "_evidence": {"stars": pr["stars"], "forks": pr["forks"], "reasons": pr["reasons"], "flags": pr["flags"],
                          "readme_facts": pr["readme_facts"], "packages": pr["packages"]},
        })
    oss = []
    for g in a["open_source"][:4]:
        if g.get("owner_is_user_org"):
            continue
        oss.append({"project": g["full_name"], "url": g["url"], "role": "Contributor", "summary": g.get("description") or "",
                    "startDate": (g.get("first") or "")[:7], "endDate": (g.get("last") or "")[:7], "highlights": [],
                    "_evidence": {"merged_prs": g["merged_prs"], "stars": g.get("stars"), "titles": g.get("titles")}})
    groups = {}
    for s in a["skills"]:
        if s["level"] == "weak" or s["name"] in TRIVIAL_SKILLS or s["category"] == SOFT_CATEGORY:
            continue
        label = CV_CATEGORY.get(s["category"], "Other")
        groups.setdefault(label, []).append(s["name"])
    ordered = sorted(groups.items(), key=lambda kv: (kv[0] != "Languages", -len(kv[1])))
    skills = [{"name": k, "keywords": v[:10]} for k, v in ordered][:6]
    loc = p.get("location") or ""
    return {
        "$schema": "github-to-cv/cv@1",
        "basics": {
            "name": p.get("name") or a["login"],
            "label": target or "",
            "email": p.get("email") or "",
            "phone": "",
            "url": a.get("personal_site") or "",
            "summary": "",
            "location": {"display": loc} if loc else {},
            "profiles": profiles,
        },
        "work": [],
        "education": [],
        "projects": projects,
        "openSource": oss,
        "skills": skills,
        "certificates": [],
        "awards": [],
        "publications": [],
        "languages": [],
        "meta": {"template": None, "region": None, "paper": None, "sectionOrder": None,
                 "_note": "Draft from GitHub data only. Fill work/education from the user; write highlights; delete _evidence when done (renderer ignores _ keys)."},
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("github_json")
    ap.add_argument("--jd", help="Job description text file")
    ap.add_argument("--target", help="Target role title, e.g. 'Backend Engineer'")
    ap.add_argument("--out-dir")
    ap.add_argument("--top", type=int, default=8)
    args = ap.parse_args(argv)

    gh = load_json(args.github_json)
    jd_text = Path(args.jd).read_text(encoding="utf-8") if args.jd else None
    a = analyze(gh, jd_text=jd_text, target=args.target, top=args.top)
    out = Path(args.out_dir) if args.out_dir else Path(args.github_json).parent
    save_json(a, out / "analysis.json")
    (out / "analysis.md").write_text(to_markdown(a), encoding="utf-8")
    draft_path = out / "cv.draft.json"
    save_json(draft_cv(a, args.target), draft_path)
    print(f"✓ Wrote {out/'analysis.md'}, {out/'analysis.json'}, {draft_path}")
    print(f"  Featured candidates: {', '.join(a['featured'][:6]) or 'none'}")
    if a.get("jd_coverage"):
        c = a["jd_coverage"]
        print(f"  JD coverage from GitHub alone: required {c['required_pct']}%, preferred {c['preferred_pct']}%")
        if c["required_missing"]:
            print(f"  Ask the user about: {', '.join(c['required_missing'][:8])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
