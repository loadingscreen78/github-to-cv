# cv.json schema

`cv.json` is [JSON Resume](https://jsonresume.org/schema) compatible. Any JSON Resume file
renders as-is. There are three additions: `openSource`, `customSections` and `meta`. Keys
starting with `_` (like the draft's `_evidence`) are ignored by the renderer.

Dates: `"YYYY-MM"` (preferred), `"YYYY"`, or `"YYYY-MM-DD"`. Omit `endDate` for "Present".
A future `endDate` on education renders as "Expected May 2027".

```jsonc
{
  "basics": {
    "name": "Jordan Lee",
    "label": "Senior Backend Engineer",            // headline: mirror the target title if true
    "email": "jordan.lee@example.com",
    "phone": "+1 (555) 010-0199",
    "url": "https://jordanlee.example.com",         // personal site / portfolio
    "summary": "Backend engineer with 8 years…",    // 2–4 lines, no pronouns
    "location": { "city": "Austin", "region": "TX", "countryCode": "US" },  // or { "display": "Pune, India" }
    "profiles": [
      { "network": "LinkedIn", "url": "https://www.linkedin.com/in/…" },
      { "network": "GitHub", "username": "jordanlee", "url": "https://github.com/jordanlee" }
    ]
  },

  "work": [{
    "name": "Northwind Pay",                         // company
    "position": "Senior Software Engineer",
    "location": "Austin, TX",                        // or "Remote"
    "url": "https://…",                              // optional, not rendered for work
    "startDate": "2023-04", "endDate": null,         // omit/null = Present
    "summary": "Optional one-line scope (team, product).",
    "highlights": ["Led …", "Cut …"]
  }],                                                // consecutive roles at the same company are grouped (promotions)

  "projects": [{
    "name": "Ledgerline",
    "description": "Optional one-liner shown above bullets",
    "url": "https://github.com/…/ledgerline",       // rendered as plain-text link
    "homepage": "https://ledgerline.dev",            // optional second link (live demo, PyPI page)
    "keywords": ["Go", "PostgreSQL", "gRPC"],        // tech stack line
    "startDate": "2024-02", "endDate": "2025-01",    // optional; hide all project dates with meta.projectDates=false
    "highlights": ["…"]
  }],

  "openSource": [{                                   // extension: contributions to others' projects
    "project": "encode/httpx", "url": "https://github.com/encode/httpx",
    "role": "Contributor",                           // or Maintainer, Core contributor, Triage
    "startDate": "2024-04", "endDate": "2025-11",
    "summary": "", "highlights": ["3 merged PRs to the 13.9k-star …"]
  }],

  "education": [{
    "institution": "The University of Texas at Austin",
    "studyType": "B.S.", "area": "Computer Science",  // rendered "B.S. in Computer Science"
    "location": "Austin, TX",
    "startDate": "2014-08", "endDate": "2018-05",
    "score": "GPA 3.8/4.0",                          // free text: "CGPA 9.1/10", "First-class honours", "Advisor: …"
    "courses": ["Distributed Systems", "Databases"]  // rendered as "Relevant coursework: …"
  }],

  "skills": [{ "name": "Languages", "keywords": ["Go", "Python", "SQL"] }],
  "certificates": [{ "name": "AWS Certified Solutions Architect – Associate", "issuer": "Amazon Web Services", "date": "2022-09", "url": "" }],
  "awards": [{ "title": "1st place, HackNorth 2025", "awarder": "120 teams", "date": "2025-02", "summary": "" }],
  "publications": [{
    "name": "Paper title", "authors": "M. Fernandes, R. Okafor, A. Lindqvist",   // extension: authors → your name is bolded
    "publisher": "NeurIPS", "releaseDate": "2025-12", "url": "https://arxiv.org/abs/…",
    "note": "Oral presentation"                                                   // extension
  }],
  "volunteer": [{ "organization": "PyCon India", "position": "Volunteer, Program Committee", "startDate": "2024", "highlights": [] }],
  "languages": [{ "language": "English", "fluency": "Fluent" }],
  "interests": [{ "name": "Open-source hardware", "keywords": [] }],

  "customSections": [                                // extension: any extra section
    { "id": "talks", "title": "Invited Talks",
      "entries": [{ "title": "Talk title", "subtitle": "Venue", "date": "Feb 2026", "location": "", "url": "", "highlights": [] }] },
    { "id": "service", "title": "Service", "items": ["Reviewer: NeurIPS, ICLR"] },          // bullet list
    { "id": "extras", "title": "Additional", "items": ["…"], "inline": true }               // one line, " | " separated
  ],

  "meta": {
    "template": "modern",              // modern | classic | minimal | executive | academic | compact | <custom>
    "region": "us",                    // us ca uk ie de fr nl eu in au nz sg me apac global → paper, Resume/CV, date style
    "level": "senior",                 // new-grad | junior | mid | senior | staff | academic (used by ats_check length rules)
    "maxPages": 1,                     // renderer shrinks type to ≤ 88% to fit, then warns
    "sectionOrder": ["summary", "skills", "work", "projects", "openSource", "education"],  // custom ids allowed
    "hideSections": ["interests"],
    "sectionTitles": { "work": "Professional Experience" },
    "accent": "#1f4e79",
    "paper": "letter",                 // overrides region
    "dateStyle": "mon-yyyy",           // mon-yyyy | month-yyyy | mm/yyyy | yyyy | yyyy-mm
    "dateSeparator": " – ",
    "entryStyle": "title-first",       // title-first | org-first | inline (overrides template)
    "skillsStyle": "lines",            // lines | inline
    "showLinks": true,                 // project/OSS URLs
    "projectDates": true,
    "fontSize": 10.5,                  // base pt (template default otherwise)
    "margins": "0.55in 0.6in",
    "documentWord": "Resume",          // overrides region ("CV")
    "fileName": "Jordan_Lee_Resume",   // output basename
    "language": "en"                   // html lang; translate headings with sectionTitles
  }
}
```

### Section ids
`summary` (from `basics.summary`), `skills`, `work`, `projects`, `openSource`, `education`,
`certificates`, `awards`, `publications`, `volunteer`, `languages`, `interests`, `references`,
plus any `customSections[].id`.

### Default headings
Summary · Skills · Experience · Projects · Open Source Contributions · Education · Certifications ·
Awards · Publications · Volunteering · Languages · Interests. Templates rename some of these
(for example, Executive uses "Professional Experience" and "Core Competencies"). Keep custom headings standard enough
for ATS to recognise.
