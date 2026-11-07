#!/usr/bin/env python3
"""Scaffold a new template from an existing one (for "bring your own template").

Usage:
    python new_template.py my-style --from modern [--display "My Style"] [--accent "#7a1f5c"]

Creates templates/my-style/ with manifest.json, style.css and template.html.j2 copied
from the base template. Then edit style.css (look) and manifest.json (section order,
titles, entry layout, DOCX fonts) and render with --template my-style.
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import TEMPLATES_DIR, load_json, save_json  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("name", help="New template id (lowercase, dashes)")
    ap.add_argument("--from", dest="src", default="modern", help="Template to copy (default: modern)")
    ap.add_argument("--display", help="Display name")
    ap.add_argument("--accent", help="Accent colour, e.g. #7a1f5c")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args(argv)

    if not re.fullmatch(r"[a-z0-9][a-z0-9\-]*", args.name) or args.name.startswith("_"):
        raise SystemExit("Template id must be lowercase letters, digits and dashes.")
    src, dst = TEMPLATES_DIR / args.src, TEMPLATES_DIR / args.name
    if not (src / "manifest.json").exists():
        raise SystemExit(f"Source template '{args.src}' not found.")
    if dst.exists() and not args.force:
        raise SystemExit(f"{dst} exists (use --force to overwrite).")
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    m = load_json(dst / "manifest.json")
    m["name"] = args.name
    m["displayName"] = args.display or args.name.replace("-", " ").title()
    m["description"] = f"Custom template based on {args.src}."
    m["basedOn"] = args.src
    if args.accent:
        m["accent"] = args.accent
    save_json(m, dst / "manifest.json")
    css = (dst / "style.css").read_text(encoding="utf-8")
    (dst / "style.css").write_text(f"/* {m['displayName']} — custom template based on {args.src}.\n"
                                   "   Keep it ATS-safe: one column, real text, no icons/images, no small-caps,\n"
                                   "   letter-spacing <= 0.08em. Run tests/ or ats_check.py after changes. */\n" + css,
                                   encoding="utf-8")
    print(f"✓ Created {dst}")
    print(f"  Edit {dst/'style.css'} and {dst/'manifest.json'}, then: python render.py cv.json --template {args.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
