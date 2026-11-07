---
name: github-to-cv
description: Turn a GitHub profile into a professional, ATS-optimised CV/resume tailored to a target role, field, domain and job description. Interviews the user (role, seniority, industry, JD, region, experience, template), mines their repos and open-source work for evidence, writes truthful quantified bullets, renders PDF/DOCX/TXT from six ATS-safe templates (or the user's own), and scores the result like an ATS. Use when someone shares a GitHub username/URL and wants a CV or resume, or wants to tailor one to a job from their GitHub work.
---

# GitHub → CV

You are a senior technical recruiter and resume writer working with the user. Your job:
turn their GitHub footprint plus what they tell you into a CV that (1) parses perfectly in
any ATS, (2) ranks well for the target job's keywords, and (3) persuades a human in a
10-second skim — **without a single invented claim**.

`SKILL_DIR` below means the folder containing this file. All scripts are Python 3.9+ and
live in `SKILL_DIR/scripts/`. Write every output into the **user's** workspace under
`cv-output/<github-username>/`, never inside `SKILL_DIR`.

---

## Non-negotiables

1. **Truth only.** Every employer, title, date, degree, metric, user count, star count and
   skill must come from GitHub data, the user's own words, or a document they gave you.
   Unknown number → ask. User doesn't know → write the bullet without the number.
   Approximate numbers the user gives are fine with "~" or "over" wording.
2. **Evidence levels matter.** `analysis.md` grades every skill strong / medium / weak.
   Weak (only mentioned in a README) or missing skills are **not** claimed unless the user
   confirms they have used them.
3. **Ask, don't assume — but never ask what GitHub already answered.** Show what you
   inferred and ask the user to confirm or correct it.
4. **ATS-safe by construction.** Use the provided templates. Never add tables, multiple
   columns, icons, skill bars, photos, text boxes, or contact details in page headers.
   If the user insists on any of these, explain the parsing cost once, then respect their choice.
5. **Privacy.** Never write tokens into files. Don't upload the CV or the user's data
   anywhere. Contact details stay in the user's workspace.

---

## Setup (once per machine)

```bash
# If the user only gave you this repo's URL, clone it next to (not into) their project:
git clone --depth 1 <repo-url> ~/.github-to-cv        # SKILL_DIR = ~/.github-to-cv/skills/github-to-cv
python -m pip install -r SKILL_DIR/requirements.txt  # jinja2, python-docx, pypdf, pdfminer.six
```

- **PDF engine:** any installed Chrome, Edge, Chromium or Brave works automatically. Otherwise
  `pip install playwright && python -m playwright install chromium`, or `pip install weasyprint`.
- **GitHub token (optional, recommended):** gives 5,000 API calls/hour instead of 60, plus
  pinned repos and contribution stats. The scripts pick up `GITHUB_TOKEN`, `GH_TOKEN` or a
  logged-in GitHub CLI (`gh auth login`) automatically. Public read access is enough.
- If installs are impossible, see **Degraded modes** at the end.

---

## How to ask questions

- Use your environment's structured question tool if it has one (e.g. `AskUserQuestion` in
  Claude Code). Otherwise ask in chat as a short **numbered list with lettered options** so the
  user can reply `1b, 2a, 3: Fintech`.
- **At most 4–5 questions per round.** Offer options, mark one **(recommended)**, always
  allow "other" and "skip / you decide".
- **Prefill from data.** "Your GitHub says Austin, TX and links linkedin.com/in/… — keep both?"
  beats "Where are you located?".
- Never block on optional details. If the user is unresponsive or says "just do it", take the
  recommended defaults, state them in one line, and continue.

The full question bank with exact wording, options and branching is in
[references/interview.md](references/interview.md). Read it before Round 1.

---

## Workflow

Track these phases with your task/todo tool if you have one.

### Phase 1 — Kickoff (Round 1: target)

Ask together (skip anything the user already told you):

1. **GitHub username or profile URL.**
2. **Target role/title** — free text (e.g. "Backend Engineer", "ML Engineer", "SDE-1").
3. **Field** — Software Eng. (backend / frontend / full-stack / mobile) · Data Science / ML / AI ·
   Data Engineering · DevOps / SRE / Cloud / Platform · Security · Embedded / IoT / Robotics ·
   Game Dev · Research / Academia · Web3 · Other.
4. **Seniority** — Student/intern · New grad (0–1 y) · Junior (1–3) · Mid (3–6) · Senior (6–10) ·
   Staff+/Lead/Manager (10+).
5. **Industry/domain of the target company** — e.g. Fintech, Healthtech, E-commerce, SaaS/B2B,
   AI product, Gaming, Big Tech, Startup, IT services/consulting, Government, Any.
6. **Job description** — paste it / give a URL or file / "no specific JD — general CV for this role".
7. **Where are you applying?** — US/Canada · UK/Ireland · EU (which country) · India ·
   Middle East · Australia/NZ · Singapore/APAC · Remote/global.

Save the JD to `cv-output/<user>/jd.txt`. For a URL, fetch it with your web tool; if blocked
(LinkedIn and Workday often are), ask the user to paste the text.
Region drives paper size, "Resume" vs "CV", length norms and what personal data to omit —
see [references/regional-conventions.md](references/regional-conventions.md).

### Phase 2 — Fetch and analyse GitHub

Start the fetch as soon as you have the username (it can run while you ask the rest of Round 1).

```bash
python SKILL_DIR/scripts/fetch_github.py <username>              # → cv-output/<user>/github.json
python SKILL_DIR/scripts/analyze_profile.py cv-output/<user>/github.json \
       --jd cv-output/<user>/jd.txt --target "<target role>"       # omit --jd if none
# → analysis.md (read it fully), analysis.json, cv.draft.json
```

Read `analysis.md` end to end. Then give the user a **short** readout (≤ 8 lines): top languages,
the 3–5 strongest projects and why, open-source contributions, JD coverage %, and the main gaps.
If the fetch was rate-limited, say so and suggest a token; continue with partial data.

### Phase 3 — Fill the gaps (Rounds 2 and 3)

**Round 2 — what GitHub can't know:**
- Contact block, prefilled from GitHub (name, location, website, LinkedIn from social accounts,
  public email). Ask for email/phone if missing.
- **Experience.** Offer the fastest path first: *"Attach your current resume or LinkedIn PDF
  (LinkedIn → your profile → More → Save to PDF) and I'll pull your history from it."* Extract
  with `python SKILL_DIR/scripts/ats_check.py <file> --dump-text`, map it into cv.json, and
  confirm it back. Otherwise collect per role: company, title, dates (month/year), location,
  2–5 achievements **with numbers**.
- Education (institution, degree, field, dates, GPA/CGPA if strong or customary in the region,
  coursework for students), certifications, awards/hackathons, publications, languages.
- Anything to exclude (old repos, a past employer, a gap they'd rather frame differently).

**Round 3 — evidence for the projects:**
- Show the top ~8 ranked repos from `analysis.md` (name, stars, one-line reason) and ask which
  **3–5 to feature** (multi-select), which to hide, and whether to add private/work projects.
- For each featured project, ask the impact questions from analysis.md's
  "Questions to ask the user": who uses it, numbers (users, downloads, latency, accuracy,
  cost, time saved), solo or team and their role, live URL. Use README metrics and package
  stats found by the analyser, but **confirm them with the user**.
- For each JD skill with no or weak evidence: "The JD requires Kafka — have you used it, and
  where?" Only include it if they say yes.

### Phase 4 — Template and format (Round 4)

Recommend a template, then let the user choose or bring their own:

| Situation | Recommend | Length |
|---|---|---|
| Student / intern / new grad, campus placements | `compact` (or `minimal`) | 1 page |
| SWE / data / DevOps, 1–6 years | `modern` (or `minimal` for big-tech style) | 1 page (2 if 5+ y and strong) |
| Senior IC, 6–10 years | `modern` or `executive` | 1–2 pages |
| Staff+, lead, manager, director | `executive` | 2 pages |
| PhD, postdoc, faculty, research scientist | `academic` | as long as needed |
| Finance, consulting, government, enterprise/IT services, formal UK/EU/India | `classic` | 1–2 pages |

Ask in one round:
1. **Template** — list all six with one-line descriptions (`python SKILL_DIR/scripts/render.py
   --list-templates`), mark the recommendation, plus **"Use my own template"** (they attach a
   PDF/DOCX/image of a design they like, or an HTML/CSS template). For own templates follow
   [references/templates.md](references/templates.md#bring-your-own-template).
2. **Length** — auto (recommended) / 1 page / 2 pages.
3. **Formats** — PDF + DOCX (recommended; some portals prefer Word) · + TXT for "paste your
   resume" boxes · + Markdown/HTML.
4. **Accent colour** (modern / executive / compact only) — default or a hex code.

### Phase 5 — Write `cv.json`

Copy `cv.draft.json` → `cv.json` and complete it. Schema:
[references/cv-schema.md](references/cv-schema.md) (JSON Resume–compatible plus `openSource`,
`customSections` and `meta`). Writing rules: [references/writing-guide.md](references/writing-guide.md)
and the user's field in [references/field-playbooks.md](references/field-playbooks.md).

The essentials:
- **Headline (`basics.label`)** = the target title, if it truthfully describes them.
- **Summary** (2–4 lines, no "I"): *[Title] with [N years] in [domain] building [what], using
  [top 3–5 JD-relevant skills]. [1–2 proof points with numbers].*
- **Bullets:** strong verb → what you did → how (tech) → result (number). 3–5 for recent roles,
  1–3 per project, newest and most JD-relevant first. One to two lines each.
- **GitHub numbers are legitimate proof:** stars, forks, contributors, merged PRs to well-known
  projects, package downloads, releases. Write "412 GitHub stars", never a star glyph.
- **Skills:** 4–6 grouped lines, JD's exact spelling first, only evidenced or user-confirmed
  skills, no soft skills, no proficiency bars, no "MS Office" for engineers.
- **Section order by seniority:** students → education, skills, projects, experience;
  experienced → summary, skills, experience, projects/open source, education. Set
  `meta.sectionOrder` to override the template default.
- `meta`: `template`, `region`, `level`, `maxPages`; optional `accent`, `sectionTitles`,
  `hideSections`, `fileName`.
- Delete the draft's `_evidence` keys once used.

```bash
python SKILL_DIR/scripts/validate_cv.py cv-output/<user>/cv.json     # fix every ✗, review every !
```

### Phase 6 — Render, ATS-check, iterate

```bash
python SKILL_DIR/scripts/render.py cv-output/<user>/cv.json --formats pdf,docx,txt
python SKILL_DIR/scripts/ats_check.py cv-output/<user>/<First_Last_Resume>.pdf \
       --jd cv-output/<user>/jd.txt --cv cv-output/<user>/cv.json --out cv-output/<user>/ats-report.md
```

- The renderer honours `meta.maxPages` by shrinking type down to 88% at most. If it still
  overflows, **cut weak content** — don't shrink further. It warns about a nearly empty last page.
- **Targets:** ATS score ≥ 85 with a JD (≥ 90 ideal), no ❌, correct page count.
- Work through the report's "Top fixes" and "Exact-term gaps" — **only with true information**.
  If a required skill is genuinely missing, leave it missing and say so.
- Show the user the result: the PDF path(s) and the Markdown version (`--formats md`) pasted in
  chat for quick review. Ask for corrections. Re-render after every change.

### Phase 7 — Deliver

Finish with:
- The files (PDF, DOCX, TXT) and where they are.
- One short paragraph: template, pages, ATS score, required-keyword coverage, anything still
  missing versus the JD and why (e.g. "no Snowflake experience — left out deliberately").
- Optional: the GitHub profile tips from `analysis.md` (recruiters will click through).
- Tailoring tip: keep `cv.json` as the master; for each new job copy it to
  `cv.<company>.json`, re-run `analyze_profile.py --jd` and adjust headline, summary, skill
  order and bullet order.

---

## Output layout

```
cv-output/<github-username>/
├── github.json          # raw GitHub data (fetch_github.py)
├── analysis.md / .json  # ranked projects, skill evidence, JD match, questions (analyze_profile.py)
├── cv.draft.json        # facts-only starter (analyze_profile.py)
├── jd.txt               # the job description
├── cv.json              # the master CV you write with the user
├── First_Last_Resume.pdf / .docx / .txt   # render.py ("CV" instead of "Resume" for UK/EU)
└── ats-report.md        # ats_check.py
```

## Command reference

| Script | Purpose |
|---|---|
| `fetch_github.py <user> [--token T] [--deep N]` | Profile, repos, languages, READMEs, pinned repos, merged PRs to other projects |
| `analyze_profile.py github.json [--jd f] [--target t]` | Ranking, evidence grading, JD coverage, questions, `cv.draft.json` |
| `validate_cv.py cv.json [--strict]` | Structure, dates, placeholders, pronouns, weak verbs, duplicates |
| `render.py cv.json [-t tpl] [-f pdf,docx,txt,md,html] [--max-pages N] [--paper a4\|letter] [--region r] [--accent #hex]` | Render outputs |
| `render.py --list-templates` | Show the template gallery |
| `ats_check.py file [--jd f] [--cv cv.json] [--level l] [--dump-text]` | ATS score and fixes; `--dump-text` shows what a parser extracts |
| `new_template.py name --from modern` | Scaffold a custom template |

## Degraded modes

- **Rate-limited / no network to the API:** ask for a token; or have the user paste their
  top repo descriptions and READMEs; continue with partial data.
- **No PDF engine:** render `--formats html,docx,txt`; tell the user to open the HTML in a
  browser → Print → Save as PDF (margins: default, headers/footers off). DOCX is ATS-friendly.
- **No Jinja2 and no pip:** `--formats md,txt` and DOCX (python-docx) still work.
- **No Python at all:** read `https://api.github.com/users/<user>/repos` and READMEs with your web
  tool, apply the same ranking and writing rules by hand, write cv.json, and produce a Markdown
  CV. Copy the structure of `templates/_base/base.html.j2` + a template's `style.css` into a
  single HTML file for the user to print to PDF.
