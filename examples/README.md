# Examples

Everything here is **fictional**: people, companies, URLs and numbers.

| File | What it is |
|---|---|
| `senior-backend.cv.json` | Senior backend engineer (US, Letter): promotions at one company, projects, open source |
| `new-grad.cv.json` | Final-year B.Tech student (India, A4): education-first, projects, internship, achievements |
| `researcher.cv.json` | PhD candidate (UK, A4): publications, research software, teaching/talks/service as custom sections |
| `sample-github.json` | Output-shaped fixture for `fetch_github.py` (used by tests and for trying `analyze_profile.py` offline) |
| `sample-jd.txt` | A backend job description for keyword-matching demos |
| `output/*.pdf`, `previews/*.png` | Rendered with `python tools/build_previews.py` |

Try the pipeline offline:

```bash
S=../skills/github-to-cv/scripts
python $S/analyze_profile.py sample-github.json --jd sample-jd.txt --target "Senior Backend Engineer" --out-dir /tmp/demo
python $S/render.py senior-backend.cv.json -t executive -f pdf,docx,txt -o /tmp/demo
python $S/ats_check.py /tmp/demo/Jordan_Lee_Resume.pdf --jd sample-jd.txt --cv senior-backend.cv.json
```
