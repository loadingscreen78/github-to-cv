# AGENTS.md — github-to-cv

Instructions for AI coding agents (Claude Code, Cursor, GitHub Copilot, Windsurf, Cline,
OpenAI Codex, Gemini CLI, Jules, Amp, Zed, Aider, …).

## If a user gave you this repository to make their CV

You are running the **github-to-cv** skill. Its complete workflow is in
[`skills/github-to-cv/SKILL.md`](skills/github-to-cv/SKILL.md). Follow it step by step.

1. **Get the files.** If this repo is not already on disk, clone it *outside* the user's project:
   `git clone --depth 1 https://github.com/loadingscreen78/github-to-cv ~/.github-to-cv`
   → `SKILL_DIR=~/.github-to-cv/skills/github-to-cv`
   (If you are already inside this repo, `SKILL_DIR=./skills/github-to-cv`.)
2. **Install:** `python -m pip install -r $SKILL_DIR/requirements.txt`
   (PDF output uses any installed Chrome/Edge/Chromium; see SKILL.md → Setup.)
3. **Read** `$SKILL_DIR/SKILL.md` and `$SKILL_DIR/references/interview.md`.
4. **Start the interview (Round 1)**: GitHub username, target role, field, seniority, industry,
   job description, region. Ask in short batches (≤ 5 questions) with options. Use your
   structured question tool if you have one.
5. Run the pipeline exactly as SKILL.md describes (fetch → analyse → interview rounds 2–4 →
   write `cv.json` → validate → render → ATS check → iterate → deliver).
6. Write all outputs to the **user's workspace** in `./cv-output/<github-username>/`.

**Hard rules:** never invent employers, dates, degrees, metrics or skills. Only use the
ATS-safe templates (or a custom one that follows the same rules). Never write tokens to
disk. Don't upload the user's data anywhere.

## If you are developing this repository

```
skills/github-to-cv/
  SKILL.md                 # the agent workflow (source of truth)
  references/              # interview, ATS rules, writing guide, playbooks, schema, templates
  scripts/                 # fetch_github, analyze_profile, render, ats_check, validate_cv, new_template
  scripts/data/            # skills taxonomy (+ implications), action verbs
  templates/_base/         # shared ATS-safe HTML skeleton + base.css
  templates/<name>/        # manifest.json + style.css + template.html.j2
examples/                  # fictional sample CVs, GitHub fixture, JD, rendered previews
tests/                     # unittest suite (PDF tests auto-skip without a browser)
tools/build_previews.py    # re-render examples/output + examples/previews
```

- Run tests: `python -m unittest discover -s tests -v`
- Scripts are standard library + optional `jinja2`, `python-docx`, `pypdf`, `pdfminer.six`.
  Keep them importable without optional packages (import them lazily).
- **Template rules (tested):** one column; real text only; contact info in the body;
  no `font-variant: small-caps`; `letter-spacing` ≤ 0.08em; bullets stay as inline "•" text
  with a hanging indent (see `base.css`). Wider tracking or small-caps break PDF text
  extraction ("P R O F E S S I O N A L").
- New template: `python skills/github-to-cv/scripts/new_template.py <name> --from modern`,
  then add it to the table in `references/templates.md` and run `tools/build_previews.py`.
- Taxonomy additions go in `scripts/data/skills_taxonomy.json`. Add a test case when you
  add a custom regex (`"p"`).
- Never add real people's data to examples. Use `example.com` emails and 555-01xx phone numbers.
