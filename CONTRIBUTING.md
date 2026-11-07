# Contributing

Thanks for helping make github-to-cv better. Good first contributions:

- **Templates.** Scaffold with `python skills/github-to-cv/scripts/new_template.py <name> --from modern`,
  style it, add a row to `skills/github-to-cv/references/templates.md`, then run
  `python tools/build_previews.py`. Templates must pass the ATS rules in the test suite:
  one column, real text, no small-caps, letter-spacing ≤ 0.08em, no images or icon fonts.
- **Skills taxonomy.** Add skills, aliases or implications to
  `skills/github-to-cv/scripts/data/skills_taxonomy.json`. Use `"cs": true` for words that are also
  common English (React, Express, Go). Add a test for any custom regex (`"p"`).
- **Field playbooks and regional conventions.** Improve `references/field-playbooks.md` or
  `references/regional-conventions.md`, and cite sources in the PR when you state a norm.
- **Interview flow.** Improve `references/interview.md`. Keep rounds to 5 questions or fewer.

## Development

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v      # PDF tests need Chrome/Chromium, Playwright or WeasyPrint
```

Principles:
1. **Truth first.** No feature may invent or inflate user facts.
2. **ATS-safe by default.** Anything that risks parsing goes behind an explicit opt-in.
3. **Standard library first** in scripts. Optional packages are imported lazily with a helpful error.
4. **Agent-agnostic.** Instructions live in `SKILL.md`/`AGENTS.md`; tool-specific files only point there.
5. **Fictional examples only.** Use `example.com` emails and 555-01xx phone numbers.
