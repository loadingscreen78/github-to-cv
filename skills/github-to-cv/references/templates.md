# Templates

All six templates share one ATS-safe skeleton (`templates/_base/base.html.j2` + `base.css`)
and differ in typography, colour, header, entry layout and default section order. Each is a
folder with `manifest.json`, `style.css` and `template.html.j2`. The renderer produces PDF
(via a browser engine), DOCX (python-docx, fonts and colours from the manifest), TXT and Markdown
from the same content.

| Template | Look | Entry layout | Default order | Pages | Best for |
|---|---|---|---|---|---|
| **modern** | Sans-serif (Inter / Segoe UI / Helvetica), navy accent, left header with rule | title-first | summary, skills, experience, projects, OSS, education | 1–2 | Most tech roles; the default |
| **classic** | Serif (Georgia / Cambria), centred uppercase name, double rule | company-first | summary, experience, projects, education, skills | 1–2 | Finance, consulting, government, enterprise/IT services, formal UK/EU/India |
| **minimal** | Black-only sans, dense, centred, ruled headings | title-first | summary, experience, projects, OSS, education, technical skills | 1 | Big-tech SWE, new grads, one-pagers |
| **executive** | Serif headings + sans body, teal-navy accent, keyword block | company-first, promotions grouped | summary, core competencies, experience, projects, OSS, education | 2 | Senior/staff/principal, managers, directors |
| **academic** | Serif (Charter / Cambria), burgundy uppercase headings, numbered publications | title-first | interests, education, publications, experience, research software, awards, custom | 2+ | PhD, postdoc, faculty, research scientist |
| **compact** | Calibri-style sans, teal accent, one-line entry headers | inline | education, skills, projects, experience, OSS, achievements | 1 | Students, interns, campus placements |

`python scripts/render.py --list-templates` prints the same list. Rendered examples are in the
repo's `examples/previews/`.

### Choosing quickly
- Unsure → **modern**.
- One page with lots of projects → **compact** (students) or **minimal**.
- Conservative industry or older ATS → **classic** (also send DOCX).
- 10+ years or managing people → **executive**.
- Publications matter → **academic**.

---

## Customising without a new template

Everything below goes in `cv.json → meta` (see [cv-schema.md](cv-schema.md)):
`accent`, `sectionOrder`, `hideSections`, `sectionTitles`, `entryStyle` (`title-first` / `org-first` /
`inline`), `skillsStyle` (`lines` / `inline`), `fontSize`, `margins`, `paper`, `dateStyle`,
`showLinks`, `projectDates`, `maxPages`.

---

## Bring your own template

The user may want their own look: "make it look like this PDF", a DOCX they love, a screenshot,
or their own HTML/CSS. Steps:

1. **Look at the reference.** Read the file or image. Note fonts (serif/sans), alignment, header
   style, colours, heading treatment (caps, rules), entry layout (title or company first; dates
   right-aligned or inline), spacing density, section order and heading names.
2. **Check it against ATS rules.** If the reference has two columns, a sidebar, a photo, icons,
   skill bars, tables, or text in headers/footers, tell the user once and briefly:
   > Your reference uses a two-column sidebar and icons, which many ATS mis-read (columns get interleaved, icons become garbage). I'll recreate the look (fonts, colours, header, spacing) in a single-column ATS-safe version. If you'd rather keep the sidebar for human-only sharing (email, printed), I can make that too as a second file.
3. **Scaffold** from the closest built-in template:
   ```bash
   python SKILL_DIR/scripts/new_template.py their-style --from modern --display "Their Style" --accent "#7a1f5c"
   ```
4. **Edit** `templates/their-style/style.css`. Change the CSS custom properties first
   (`--font-body`, `--font-head`, `--accent`, `--text`, `--muted`, `--rule`, `--name-size`, `--h2-size`,
   `--section-gap`, `--entry-gap`, `--lh`, `--bullet`), then header, section-title and entry rules.
   Edit `manifest.json` for `entryStyle`, `headerAlign` (`left` / `center`), `sectionTitles`,
   `defaultSectionOrder`, `skillsStyle`, `basePt`, `margins`, and `docx` (font, size, alignment,
   colours) so the Word version matches.
5. **Structural changes** (rare): override blocks in `template.html.j2` (`header`, `sections`,
   `section` (scoped, receives `s`), `head_extra`). Keep the `cv-header`, `section-title` and
   `.bullets` structure so text extraction stays clean.
6. **Keep the ATS rules** (enforced by the tests): no `font-variant: small-caps`, letter-spacing
   ≤ 0.08em, no images or icon fonts, contact info in the body, one column.
7. **Render and verify:**
   ```bash
   python SKILL_DIR/scripts/render.py cv.json --template their-style -f pdf,docx
   python SKILL_DIR/scripts/ats_check.py <file>.pdf --cv cv.json
   ```
   Look at the PDF. If you can render pages to images (e.g. `pdftoppm -png -r 80`), compare
   them side by side with the reference and iterate until it matches.
8. **If the user insists on a non-ATS design** (photo, sidebar): build it as a separate template
   (e.g. `their-style-visual`), make sure the ATS-safe version is the one they upload to portals,
   and set `"atsSafe": false` in its manifest.

**User-supplied HTML/Jinja templates** can be dropped into `templates/<name>/` directly if they
use the context variables from `base.html.j2` (`cv.name`, `cv.label`, `cv.contact_lines`,
`cv.sections[*]` with `kind`, `title`, `entries`, …). The easiest route is to extend
`base.html.j2` and port only their CSS.

**A DOCX the user wants filled in:** recreate it as a template (steps above) rather than editing
their file. Word templates with tables or text boxes are exactly what ATS mis-parse.
