# Copilot instructions — github-to-cv

This repository is an AI-agent skill that turns a GitHub profile into an ATS-optimised CV.

When the user asks for a CV/resume (from their GitHub, for a role, or for a job description):
1. Read `AGENTS.md`, then follow `skills/github-to-cv/SKILL.md` exactly.
2. Interview the user in short rounds (≤ 5 questions, with options) using
   `skills/github-to-cv/references/interview.md`: target role, field, seniority, industry,
   job description, region, then experience/education, project evidence, and template.
3. Run the scripts in `skills/github-to-cv/scripts/` from the terminal; write outputs to
   `cv-output/<github-username>/`.
4. Never invent employers, dates, metrics or skills. Use only the ATS-safe templates.

When editing the code: keep scripts standard-library-first, follow the template rules in
`AGENTS.md`, and run `python -m unittest discover -s tests`.
