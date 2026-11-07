# ATS rules (what actually matters)

An Applicant Tracking System (Workday, Greenhouse, Lever, iCIMS, Taleo/Oracle, SAP SuccessFactors,
SmartRecruiters, Ashby, Naukri RMS, Darwinbox, and others) does three things with a CV:

1. **Parses** it into fields: name, contact, roles (title, company, dates), education, skills.
   Bad parsing means empty or garbled fields and a profile recruiters skip.
2. **Searches and ranks**: recruiters filter by keywords, titles, location and years.
   Some systems also score candidates against the job (skills match, title match).
3. **Shows** the candidate profile and the original file to a human, who decides in seconds.

So the goals are: parse perfectly, contain the right literal keywords, and read well to a human.

---

## Formatting rules (all built into the templates)

| Rule | Why |
|---|---|
| **Single column, reading order = visual order** | Multi-column layouts get interleaved line by line ("Python Senior Engineer 2021 Docker…"). |
| **Contact details in the body, at the top** | Many parsers ignore page headers/footers in DOCX. |
| **No tables, text boxes, or columns for layout** | Cell order and text-box placement are unpredictable after parsing. |
| **No images, icons, logos, charts, skill bars or photos** | Not text. Icons from icon fonts become garbage (``, `(cid:42)`). |
| **Standard section headings** ("Experience", "Education", "Skills", "Projects") | Parsers locate sections by known headings. "My Journey" means no experience section. |
| **Real text bullets in reading order** | Our PDFs emit `• ` as a real character on the same line. Tested with pdfminer, pypdf and poppler. |
| **No ligatures** | "ﬁ" and "ﬂ" glyphs can be dropped ("ofice", "worklow"). Templates disable them. |
| **No small-caps; letter-spacing ≤ 0.08em** | Tested: synthesised small-caps and wide tracking make extractors split words ("P R O F E S S I O N A L"), and the heading is no longer recognised. |
| **Consistent dates, "MMM YYYY – MMM YYYY" or "Present"** | Date parsing drives "years of experience" filters. |
| **Common fonts at 10–11 pt** | Unusual fonts may lack text mappings. The templates fall back to system fonts. |
| **Plain-text URLs** (`github.com/user`) | ATS can't click links; humans need to read them. |
| **No keyword stuffing or white text** | Modern ATS show parsed text to recruiters. Hidden text is visible and disqualifying. |

`ats_check.py` verifies these on the final file, not on the source.

---

## File format

- **Follow the portal's instructions first.** If it says DOCX, send DOCX.
- **PDF (text-based)** parses well in every major modern ATS and preserves layout for humans.
  It's the default for email and most portals.
- **DOCX** is the safest choice for older or self-hosted systems (older Taleo and iCIMS setups,
  some government portals, many Indian job boards). Our DOCX uses real Word headings and list
  styles, with no tables, text boxes or header/footer content.
- **TXT** is for "paste your resume" boxes.
- **Never** upload an image-only PDF (exported from Canva or design tools as an image, or scanned).
  `ats_check.py` fails these.
- File name: `First_Last_Resume.pdf` (or `_CV` for UK/EU). Never `resume (3).pdf`.

---

## Keywords: how to win the search honestly

1. **Use the JD's exact phrases** for skills you really have: "PostgreSQL", not just "Postgres".
   "CI/CD", not only "GitHub Actions". Recruiter searches are literal. `ats_check.py` lists the
   **exact-term gaps** where your CV implies a skill but doesn't name it.
2. **Spell out key acronyms once:** "Amazon Web Services (AWS)", "Natural Language Processing (NLP)".
3. **Put keywords in two places:** the Skills section (for filters) and a bullet that shows them
   in use (for rankers and humans).
4. **Mirror the job title** in your headline if it truthfully fits ("Senior Backend Engineer").
   Title match is one of the strongest ranking signals.
5. **Soft skills go in bullets, not the skills list.** "Mentored 4 engineers" proves leadership;
   the word "Leadership" in a list proves nothing.
6. **Don't stuff.** Mentioning a skill more than about 8–10 times reads as spam to humans and some rankers.

---

## Myths vs facts

| Myth | Reality |
|---|---|
| "75% of resumes are auto-rejected by ATS." | There's no credible source for this figure. Most rejections are by humans or knock-out questions (work authorisation, location, years). Parsing quality and keywords decide whether a human finds you. |
| "ATS can't read PDFs." | Outdated. Text-based PDFs parse well in modern systems. Image PDFs and complex layouts are the problem. |
| "Use white text to hide keywords." | Parsed text is shown to recruiters, so it's visible and looks dishonest. |
| "Fancy design gets noticed." | Two-column designs, icons and photos often parse badly. Clean typography and strong content get noticed. |
| "One page, always." | One page for students and juniors. Two pages is normal for 6+ years. Academic CVs run as long as needed. |
| "An ATS score of 100 guarantees interviews." | Scores are heuristics. They catch parsing and keyword problems. Content quality and fit still decide. |

---

## Portal-specific notes

- **Workday:** re-types your CV into its own form. Check the auto-filled fields after upload.
  Dates in "MMM YYYY" parse best.
- **Greenhouse / Lever / Ashby:** good PDF parsing. Recruiters often read the original PDF, so
  design quality matters too.
- **iCIMS / Taleo (older installs):** prefer DOCX. Keep headings very standard.
- **Naukri / Indian portals:** DOCX or PDF. Recruiters search by skill keywords and notice
  period. Keep a TXT copy to paste into profile fields.
- **LinkedIn Easy Apply:** uploads go to the employer's ATS. The same rules apply.

---

## Final checklist

- [ ] `validate_cv.py` shows no ✗
- [ ] `ats_check.py` ≥ 85 (with a JD), no ❌, correct page count
- [ ] Required JD skills present **if true**, in Skills plus at least one bullet
- [ ] Headline mirrors the target title (if true)
- [ ] Name, email, phone, city and LinkedIn/GitHub at the top
- [ ] Dates consistent; no unexplained overlaps
- [ ] File named `First_Last_Resume.pdf` / `.docx`
- [ ] User has read and approved every claim
