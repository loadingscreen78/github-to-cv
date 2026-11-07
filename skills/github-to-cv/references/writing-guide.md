# Writing guide

The test for every line: **would a recruiter skimming for 10 seconds understand what you did,
with what, and why it mattered, and would it survive a follow-up question in an interview?**

Contents: [Headline](#headline) · [Summary](#summary) · [Bullets](#bullets) ·
[Turning repos into bullets](#turning-repos-into-bullets) · [Open source](#open-source-contributions) ·
[Skills](#skills-section) · [Experience details](#experience-details) · [Students](#students-and-new-grads) ·
[Tailoring](#tailoring-to-a-job-description) · [Style rules](#style-rules) · [Banned phrases](#banned-phrases)

---

## Headline

`basics.label`: the target title, if it honestly describes the person. Examples: "Senior Backend
Engineer", "Machine Learning Engineer", "Software Engineer — New Grad". Avoid "Aspiring…",
"Passionate…" and "Ninja". A specialisation can follow a separator: "Data Engineer | Streaming &
Lakehouse".

## Summary

Two to four lines, no pronouns, no clichés. Skip it for students if space is tight.
Formula:

> **[Title] with [N years] [in domain] building [what kind of systems], using [3–5 target-JD skills]. [Proof point with a number]. [Second proof point or differentiator].**

Examples:
- *Backend engineer with 8 years in payments, building high-throughput ledger and transfer systems in Go, PostgreSQL and Kafka on AWS. Led a ledger redesign to 4x throughput at 99.99% availability; maintainer of open-source tools with 800+ GitHub stars.*
- *Final-year Computer Science student (CGPA 9.1) who ships full-stack products in TypeScript, React and Node.js. Built a campus marketplace used by 1,200 students and won HackNorth Pune 2025.*

## Bullets

**Formula: Verb + what + how (tech) + result (number).** Google's version: *"Accomplished [X] as measured by [Y], by doing [Z]."*

| Weak | Strong |
|---|---|
| Responsible for the payments API. | Built the idempotent transfers API (gRPC, PostgreSQL) that processes $1.2B in annual payment volume. |
| Worked on improving performance. | Cut p99 latency from 180 ms to 45 ms by caching balance reads in Redis and adding covering indexes. |
| Helped with deployment. | Migrated 40+ services to Kubernetes (EKS) with Helm and Terraform, reducing infrastructure cost by 28%. |
| Made a chatbot using AI. | Built a retrieval-augmented Q&A assistant over 5,000 PDFs (LangChain, pgvector), raising answer accuracy from 61% to 78% on a 200-question eval set. |

Rules:
- **3–5 bullets for recent roles, 1–3 for older roles and projects.** Order by relevance to the JD.
- **One to two lines each** (~12–30 words). Split anything longer.
- **Start with a strong verb** from `scripts/data/action_verbs.json`: past tense, or present tense for the current role. Vary openers.
- **Quantify where truthful.** Aim for 60%+ of bullets with a number. Good sources:
  - scale: users, requests/sec, events/day, rows, data size, services, regions
  - speed: latency, build time, page load, time-to-deploy
  - money: revenue, cost saved, payment volume
  - quality: error rate, incidents, test coverage, accuracy/F1
  - reach: GitHub stars, forks, contributors, downloads, adopting teams
  - people: team size led, engineers mentored, students taught
- **Name the tech inside the bullet** for JD keywords: "…with Kafka", "(FastAPI, Celery)".
- **Credit honestly:** "Led", "Built" and "Owned" only if true. Otherwise "Co-built", "Contributed",
  "Implemented the X module of".
- **Approximate honestly:** "~30 tickets/month" or "over 1,000 users" when the user gives a rough
  figure. Never round up into a claim they can't defend.

## Turning repos into bullets

GitHub gives you the *what* and *how*. The interview gives you the *why* and *result*. Combine them:

1. **What it is**, in one clause, from the README or description: "Double-entry ledger service…"
2. **The hard part**, from the README, code or the user: "idempotent transfers with optimistic locking", "Raft leader election".
3. **Proof**, from GitHub or the user: stars, forks, downloads, benchmarks, users, a hackathon result, adoption.

| Source data | Bullet |
|---|---|
| Repo `ledgerline`: Go, PostgreSQL; README benchmark "4,800 transfers/sec, p99 < 35 ms"; 412★ | Open-source double-entry ledger in Go and PostgreSQL with idempotent transfers and event sourcing; sustains 4,800 transfers/sec at p99 < 35 ms; 412 GitHub stars. |
| Repo published on PyPI; user confirms ~3k monthly downloads | Published `fastapi-ratelimit-kit` on PyPI (~3k monthly downloads): async Redis-backed rate limiting with < 0.4 ms overhead per request. |
| Student repo, user says 1,200 sign-ups | Launched a student marketplace (Next.js, Node.js, PostgreSQL) adopted by 1,200 users across 3 campuses in its first semester. |

**Project entry format:** name · tech stack line · repo URL · dates (optional) · 1–3 bullets.
Use the project's real name. Rename only for readability (`k8s-preview-envs` → "K8s Preview Envs"
is fine; inventing a brand name is not).

**What not to feature:** tutorial and course clones, to-do/calculator/weather apps (unless
substantially extended), forks with no changes, dotfiles. The analyser flags these. Competitive
programming repos become an Achievements line ("LeetCode rating 2,050, top 3%"), not a project.

## Open-source contributions

Merged PRs to well-known projects are strong, verifiable evidence. Format:

> **encode/httpx** · Contributor · Apr 2024 – Nov 2025
> • 3 merged PRs to the 13.9k-star Python HTTP client, including a fix for a connection-pool leak on cancelled requests.

- Write "13.9k-star", never "★".
- Lead with impact: what the PR fixed or enabled, not "fixed typos". Docs PRs can be grouped:
  "Improved docs and examples (4 merged PRs)".
- Contributions to your employer's org repos are **work**. Put them under the job, not under Open Source.
- Maintainer roles, release management and triage count. Ask the user.

## Skills section

- **4–6 lines**, grouped: *Languages · Frameworks/Backend · Data/ML · Cloud & DevOps · Databases · Tools*
  (adapt per field).
- **Target-JD skills first**, in the JD's spelling.
- **Only evidenced skills:** strong or medium in the analysis, or confirmed by the user. Ten honest
  skills beat thirty claimed ones.
- No proficiency bars, stars, percentages or "Beginner/Expert" labels. If the user insists, add a
  short "Familiar with:" tail for lighter skills.
- No soft skills, no "Microsoft Word" or "Windows" for engineering roles, no "HTML" for senior backend roles
  unless the JD asks.
- Cloud services in parentheses help keyword search: "AWS (EKS, Lambda, S3, RDS)".

## Experience details

- Title exactly as held. If it's unusual internally, add the standard equivalent:
  "Member of Technical Staff (Software Engineer)".
- Promotions: list consecutive roles at the same company with the same company name. The renderer
  groups them under one heading automatically.
- Internships are experience. Label them ("Software Engineering Intern").
- Dates: month + year. Current role: no `endDate`, which renders "Present".
- Location: "City, ST", "City, Country" or "Remote".

## Students and new grads

- **Education first** (CGPA if strong or customary), then skills, projects, experience/internships, achievements.
- 3–4 projects with real depth beat 8 shallow ones.
- Hackathons, competitive programming, teaching assistantships, campus tech-club leadership and
  open-source programmes (GSoC, Hacktoberfest with merged PRs, MLH) are real evidence.
- Coursework line: 4–6 courses that match the JD.
- India campus format: include Class XII/X scores only if the employer or placement cell asks.

## Tailoring to a job description

1. Run `analyze_profile.py --jd` and read the JD coverage table.
2. Headline → the JD title (if true). Summary → its top 3–5 required skills plus one domain term
   ("payments", "healthcare", "ad-tech") if the user has that background.
3. Reorder bullets so JD-relevant ones come first. Reorder skills the same way.
4. Swap featured projects for ones that match the JD better.
5. Mirror exact phrases for true skills (see the "exact-term gaps" in `ats_check.py`).
6. Never add a skill, tool or domain the user doesn't have.

## Style rules

- Implied first person: "Built…", never "I built…". No "we".
- Consistent tense: past for previous roles, present for the current one.
- Numbers: numerals ("4x", "40+", "$1.2B", "99.99%"). Units: "ms", "req/s", "GB".
- One date format everywhere (the renderer enforces it).
- Consistent punctuation: either all bullets end with a period or none do (default: they do).
- Spell tech names correctly: PostgreSQL, JavaScript, Node.js, GitHub, Kubernetes, scikit-learn, PyTorch.
- UK/EU/India spelling for those regions if the user writes that way (optimise / optimize).

## Banned phrases

"Responsible for", "Duties included", "Worked on", "Helped with", "Hard-working", "Team player",
"Detail-oriented", "Results-driven", "Self-starter", "Passionate about", "Go-getter", "Synergy",
"Think outside the box", "Proven track record" (show the record instead), "References available upon request",
"Ninja/Rockstar/Guru", "Various", "Etc.", and any emoji.
