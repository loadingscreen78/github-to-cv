# Interview playbook

The interview is what turns a list of repositories into a CV for a specific job. Ask in
**four short rounds**. Each round is at most 4–5 questions with options. Prefill from data
whenever you can, and never ask for something GitHub or an attached document already answers.

Contents: [Principles](#principles) · [Round 1: target](#round-1--target) ·
[Round 2: beyond GitHub](#round-2--beyond-github) · [Round 3: project evidence](#round-3--project-evidence) ·
[Round 4: template and format](#round-4--template-and-format) · [Review round](#review-round) ·
[Branches](#branches-by-situation) · [Hard cases](#hard-cases)

---

## Principles

- **Batch, don't drip.** One round = one message with 3–5 numbered questions. Avoid one question per message.
- **Options + recommended + escape hatch.** For example: `a) Modern (recommended) b) Classic c) … d) Other`.
- **Confirm instead of asking.** "I'll use *Jordan Lee · Austin, TX · github.com/jlee*. OK?"
- **Explain why only when it helps.** "Region decides paper size and whether to include a photo" is useful.
  Generic "this helps me tailor your CV" is noise.
- **Accept partial answers.** Fill gaps with recommended defaults and say which ones you used.
- **Never pressure for metrics.** If the user has no numbers, write a strong bullet without one.
  Don't suggest numbers for them to approve.
- **Language:** reply in the user's language; write the CV in the language of the target job
  (ask if unclear).

With a structured question tool (Claude Code's `AskUserQuestion`, etc.), use single-select for
field, seniority and region, multi-select for featured projects and output formats, and
free text for the role and JD.

---

## Round 1 — Target

Ask before or while fetching. Skip anything already given.

| # | Question | Options / format | Why it matters |
|---|---|---|---|
| 1 | What's your GitHub username or profile URL? | free text | Data source |
| 2 | Which role are you targeting? | free text; offer 2–3 guesses from bio/top languages, e.g. "Backend Engineer", "Full-Stack Developer", "ML Engineer" | Headline, keyword set, project ranking |
| 3 | Which field best describes it? | Software Eng. – backend · frontend · full-stack · mobile / Data Science–ML–AI / Data Engineering / DevOps–SRE–Cloud–Platform / Security / Embedded–IoT–Robotics / Game Dev / Research–Academia / Web3 / Other | Picks the [field playbook](field-playbooks.md) |
| 4 | Your experience level? | Student/intern · New grad (0–1 y) · Junior (1–3) · Mid (3–6) · Senior (6–10) · Staff+/Lead/Manager (10+) | Section order, length, template |
| 5 | Industry/domain of the companies you're applying to? | Fintech · Healthtech · E-commerce · SaaS/B2B · AI/ML product · Gaming · Big Tech · Early-stage startup · IT services/consulting · Government/public · Any | Domain keywords, which projects to lead with |
| 6 | Do you have a specific job description? | a) Paste it b) Link or file c) No, make a general CV for this role | Keyword targeting and ATS scoring |
| 7 | Where are you applying? | US/Canada · UK/Ireland · EU (which country?) · India · Middle East · Australia/NZ · Singapore/APAC · Remote/global | Paper, "Resume" vs "CV", length, personal-data rules |

**Example message (chat fallback):**

> Let's build your CV. Five quick questions (reply like `2a, 3c, …`):
> 1. **Target role?** e.g. "Backend Engineer". From your repos I'd guess *Backend* or *Platform Engineer*.
> 2. **Level:** a) Student b) New grad c) 1–3 yrs d) 3–6 yrs e) 6–10 yrs f) 10+
> 3. **Industry:** a) Fintech b) SaaS/B2B c) Big Tech d) Startup e) Any f) other: ___
> 4. **Job description:** paste it, give a link, or say "general".
> 5. **Applying in:** a) US/Canada b) UK/EU c) India d) Other: ___

If the user gives several JDs, pick the one they care about most for the master CV. Offer
per-company variants at the end.

---

## Round 2 — Beyond GitHub

Run this after `analyze_profile.py`, so you can prefill.

1. **Contact block (confirm/fill):** full name as it should appear; email; phone with country
   code; city + country; LinkedIn URL; portfolio/website. Prefill from `github.json` → `profile`,
   `social_accounts`, `personal_site`.
2. **Work experience.** Offer the fast path:
   > Fastest: attach your current resume or your LinkedIn PDF (LinkedIn → your profile → **More → Save to PDF**). I'll extract your roles and you just confirm. Or paste: *Company · Title · Start–End (month/year) · Location · 2–5 things you achieved, with numbers if you have them.*

   For each role you then need: company, title, start/end month and year, location (or
   "Remote"), and 2–5 achievements. Ask for **outcomes**, not duties: "What changed because
   of your work? Faster, cheaper, more users, fewer incidents? By how much?"
3. **Education:** institution, degree, field, dates (or expected graduation), GPA/CGPA (include if
   ≥ 3.5/4, ≥ 8/10, a First/2:1, or customary in the region), and relevant coursework for students
   (4–6 courses that match the JD).
4. **Extras (multi-select):** certifications · awards/hackathons/competitive programming ·
   publications/talks · volunteering/community · spoken languages · none.
5. **Exclusions:** "Anything to leave out or handle carefully? Old repos, a short stint, an employment gap?"

**When the user attaches a resume:** run `ats_check.py <file> --dump-text`. Map the result into
`work`, `education`, `certificates`, and so on. Read it back as a compact list for confirmation,
and keep their original numbers verbatim. Their old bullets are raw material. Rewrite them with
the [writing guide](writing-guide.md), but never change facts.

---

## Round 3 — Project evidence

1. **Feature selection (multi-select):** show the top ~8 from `analysis.md`:

   > Which projects should we feature? (pick 3–5)
   > 1. **ledgerline**: 412★, Go/PostgreSQL, matches JD: Go, PostgreSQL, gRPC *(recommended)*
   > 2. **fastapi-ratelimit**: 268★, published on PyPI *(recommended)*
   > 3. **k8s-preview-envs**: 95★, Terraform/Helm *(recommended)*
   > 4. tracekit: 31★, OpenTelemetry
   > 5. pg-backup-s3: 18★
   > Also: any private or work projects to add? Any repos to hide?

2. **Impact questions** for each featured project, batched. Use the analyser's generated
   questions and adapt them:
   - What problem does it solve, and for whom? Is anyone using it (you, your team, a company, public users)?
   - Numbers: users, downloads, requests/sec, latency, accuracy, cost or time saved, data size.
   - Solo or team? If team: your part, team size.
   - What was technically hardest? (Often the best bullet.)
   - Live URL or package page?
3. **README claims and package stats** the analyser found: "Your README says *4,800 transfers/sec
   at p99 < 35 ms*. Still accurate? OK to use?" Look up download stats from the analyser's
   `stats_url` with your web tool, and show the user the number before using it.
4. **JD gaps:** one line per missing or weak required skill:
   > The JD asks for **Kafka** and **distributed systems**. I didn't find them on GitHub. Have you used them at work or school? (yes + where / no)

   Never add a skill on a "maybe".
5. **Open source:** confirm the external PRs listed in the analysis are theirs and worth
   featuring (merged PRs to well-known projects are strong evidence). Ask what each PR did if
   the titles aren't self-explanatory.

---

## Round 4 — Template and format

1. **Template** (single-select, recommendation first, from the decision table in SKILL.md):
   > a) **Modern** *(recommended)*: clean sans-serif, navy accent. Best for most tech roles.
   > b) **Minimal**: dense black one-pager, the big-tech classic
   > c) **Compact**: education-first one-pager for students/new grads
   > d) **Classic**: formal serif, company-first (finance, consulting, enterprise, UK/EU/India)
   > e) **Executive**: senior/staff/manager, 2 pages, keyword block
   > f) **Academic**: publications-first research CV
   > g) **Use my own template**: attach a PDF/DOCX/image of a design you like, or HTML/CSS
2. **Length:** auto (recommended) · 1 page · 2 pages.
3. **Formats (multi-select):** PDF *(default)* · DOCX *(default)* · TXT for portal paste boxes · Markdown · HTML.
4. **Accent colour** (Modern/Executive/Compact): keep default · navy · teal · burgundy · charcoal · custom hex.

If the user can't choose, render page 1 in the top two templates and let them compare.

---

## Review round

After the first render, show the Markdown version in chat and the file paths, then ask:

> Here's the draft (ATS score **88/100**, required JD keywords **14/16**).
> 1. Anything inaccurate or overstated?
> 2. Any bullet you'd swap for something you're prouder of?
> 3. Missing keywords: **Distributed Systems**, **Message Queues**. Add them only if true; for example, your Kafka work could be phrased as "message queues (Kafka)". OK?
> 4. Happy with the template and length?

Iterate until the user approves. Re-run `validate_cv.py`, `render.py` and `ats_check.py` after each change.

---

## Branches by situation

**Student / new grad.** Ask for GPA/CGPA, coursework, internships, hackathons, competitive
programming ratings, campus roles, and (India) Class X/XII scores if the campus format requires
them. Projects carry the CV: dig deeper in Round 3 and allow 3–5 projects. Use `compact` or `minimal`.

**Experienced engineer whose GitHub is mostly empty or old.** Work experience carries the CV.
Use GitHub as a supporting "Projects / Open Source" section, or drop it if weak. Say this kindly:
"Your strongest evidence is your work. I'll lead with that." Get a resume or LinkedIn PDF in Round 2.

**Career switcher.** Ask about transferable achievements from the previous career (leadership,
domain expertise, analytics). Lead with a summary that bridges ("Former financial analyst turned
data engineer…") and with projects that match the target. Consider `classic` or `modern`.

**Researcher / academic.** Ask for publications (authors in order, venue, year, links), talks,
teaching, grants, reviewing or service, and advisor and thesis title. Use `academic`. Research
software repos go under "Research Software" with citation or star counts.

**Manager / staff+.** Ask for team size, org scope, budget, hiring, cross-team initiatives,
and strategy outcomes. GitHub is a minor signal here. Use `executive`, 2 pages.

**Freelancer / contractor.** Group clients under one "Independent Consultant" role with
client-by-client bullets. Ask for NDA constraints before naming clients.

**Employment gap.** Don't ask why unless the user raises it. Offer neutral options: leave
dates in years only, or add a one-line entry ("Career break: caregiving / study / travel,
2023–2024"). Projects built during the gap are good evidence.

---

## Hard cases

| Situation | What to do |
|---|---|
| User asks you to "add skills from the JD" they don't have | Decline politely. Explain that interviews and background checks catch it. Offer adjacent true phrasing ("Event streaming with Redis Streams; learning Kafka" belongs in a cover letter, not the skills list). |
| User wants numbers made up ("just put 40%") | Ask what they actually observed. If they truly estimate it, use their estimate with "~" and note it in the delivery summary. Never invent one yourself. |
| Team project; user's role unclear | Ask. Use "Contributed", "Co-built" or "Owned the X module" accordingly. Never "Built" for something they joined late. |
| Repo is a fork with real work | Confirm what they changed. Describe it as "Extended X with Y". |
| Private or work code | Describe it at the level they're allowed to share. No repo links. |
| User insists on a photo or two columns | Explain once (parsing risk, discrimination norms in US/UK). If they still insist, comply in a custom template, note the trade-off, and offer an ATS-safe twin. |
| Rate-limited fetch | Ask for a token or `gh auth login`; continue with partial data meanwhile. |
| No JD | Build a role-generic CV from the field playbook's keyword set. Offer to tailor later. |
