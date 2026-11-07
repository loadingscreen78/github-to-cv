---
trigger: model_decision
description: Use when the user wants a CV or resume built from a GitHub profile, or tailored to a job description.
---

Follow `skills/github-to-cv/SKILL.md` (setup in `AGENTS.md`). Interview the user in rounds of
≤ 5 questions using `skills/github-to-cv/references/interview.md`, run the scripts in
`skills/github-to-cv/scripts/`, write outputs to `cv-output/<github-username>/`, and never
invent facts. Only ATS-safe templates.
