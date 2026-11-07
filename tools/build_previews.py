#!/usr/bin/env python3
"""Re-render the example CVs in every template and refresh the README preview images.

    python tools/build_previews.py            # needs a PDF engine + pdftoppm (poppler-utils)

Writes examples/output/<template>.pdf and examples/previews/<template>.png (page 1).
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "github-to-cv" / "scripts"))
import render  # noqa: E402

SHOWCASE = {  # template -> example that shows it best
    "modern": "senior-backend", "classic": "senior-backend", "minimal": "senior-backend",
    "executive": "senior-backend", "compact": "new-grad", "academic": "researcher",
}


def main():
    out = ROOT / "examples" / "output"
    prev = ROOT / "examples" / "previews"
    out.mkdir(parents=True, exist_ok=True)
    prev.mkdir(parents=True, exist_ok=True)
    if not shutil.which("pdftoppm"):
        print("pdftoppm not found (install poppler-utils); PDFs will be built without PNG previews.")
    for tpl, ex in SHOWCASE.items():
        tmp = Path(tempfile.mkdtemp())
        res = render.render_all(ROOT / "examples" / f"{ex}.cv.json", template=tpl, formats=["pdf"], out_dir=tmp,
                                basename=tpl, max_pages=2, quiet=True)
        pdf = out / f"{tpl}.pdf"
        shutil.copy(res["files"]["pdf"], pdf)
        if shutil.which("pdftoppm"):
            subprocess.run(["pdftoppm", "-png", "-r", "96", "-f", "1", "-l", "1", "-singlefile", str(pdf),
                            str(prev / tpl)], check=True)
        shutil.rmtree(tmp, ignore_errors=True)
        print(f"✓ {tpl:10} ← {ex}  ({res.get('pages')} page(s))")


if __name__ == "__main__":
    main()
