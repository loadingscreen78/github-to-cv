---
description: Build an ATS-optimised CV from a GitHub profile (guided interview → PDF/DOCX)
argument-hint: "[github-username-or-url] [target role]"
---

Use the **github-to-cv** skill to build a CV. Input from the user: $ARGUMENTS

Follow the skill's SKILL.md exactly: start with the Round 1 interview (skip anything already
given above), fetch and analyse the GitHub profile, complete Rounds 2–4, write cv.json,
validate, render, run the ATS check, iterate with the user, and deliver the files.
Never invent facts.
