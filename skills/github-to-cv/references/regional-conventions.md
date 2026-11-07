# Regional conventions

Set `meta.region` in cv.json. The renderer then picks the paper size, the document word
("Resume"/"CV") in the file name, and the date style. The rules below decide what goes in the content.

| Region (`meta.region`) | Paper | Called | Typical length | Photo | Personal data to omit | Notes |
|---|---|---|---|---|---|---|
| United States (`us`) | Letter | Resume | 1 page < 10 y; 2 pages senior | **No** | DOB/age, gender, marital status, nationality, religion, photo, full street address | City + state is enough. "References on request" is obsolete. |
| Canada (`ca`) | Letter | Resume | 1–2 | No | Same as US | Bilingual (EN/FR) is an asset; list it in Languages. |
| United Kingdom / Ireland (`uk`, `ie`) | A4 | CV | 2 pages normal | No | DOB, photo, marital status | UK spelling. A 2:1/First degree classification is commonly listed. |
| Germany / Austria / Switzerland (`de`) | A4 | CV (Lebenslauf) | 1–2 | Optional (traditional, declining) | — | Dates often MM/YYYY (the renderer uses `mm/yyyy` for `de`). Ask whether the role is English-language. |
| France / Benelux / Nordics / rest of EU (`fr`, `nl`, `eu`) | A4 | CV | 1–2 | Optional (FR traditional) | — | Europass is accepted in the public sector but weak for tech; our templates are better. |
| India (`in`) | A4 | Resume / CV | 1 page for freshers, 1–2 experienced | No for tech/MNCs | DOB, marital status, father's name, religion (outdated practice) | CGPA/percentage common for freshers. Notice period and current location matter for Indian recruiters (put them in the summary or a cover note if asked). |
| Middle East / Gulf (`me`) | A4 | CV | 2 | Commonly expected | — | Nationality and visa status are often asked; include only if the user wants. |
| Australia / New Zealand (`au`, `nz`) | A4 | Resume (AU) / CV (NZ) | 2–3 | No | DOB, photo | Referees section sometimes expected ("Referees available on request" is acceptable). |
| Singapore / APAC (`sg`, `apac`) | A4 | Resume | 1–2 | Optional | — | Nationality/PR status is sometimes listed for Singapore; ask. |
| Remote / global (`global`) | A4 | Resume | 1–2 | No | All of the above | State time zone or "Open to remote (UTC+5:30)" in the summary if relevant. |

## Rules of thumb
- **When in doubt, omit personal data** (photo, DOB, gender, marital status). It never helps in tech
  hiring and adds parsing and discrimination risk. If the user explicitly wants a photo for a region
  where it's customary, explain it needs a custom template and that ATS ignore or mis-parse images.
- **Work authorisation:** add one line only if it removes a likely objection ("Authorized to work in
  the US, no sponsorship required" or "Holder of UK Skilled Worker visa"), and only as the user states it.
- **Language of the CV:** match the job posting. For non-English CVs set `meta.language`
  (e.g. `"de"`) and `meta.sectionTitles` with translated headings
  (Berufserfahrung, Ausbildung, Kenntnisse, Projekte).
- **Paper** auto-switches: Letter for US/CA, A4 elsewhere. Override with `meta.paper` or `--paper`.
