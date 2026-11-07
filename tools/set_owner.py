#!/usr/bin/env python3
"""Replace the YOUR_USERNAME / YOUR_NAME placeholders after you fork or create the repo.

    python tools/set_owner.py <github-username> "<Your Name>"
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = ["README.md", "AGENTS.md", "LICENSE", ".claude-plugin/plugin.json", ".claude-plugin/marketplace.json"]


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        return 1
    user, name = sys.argv[1].lstrip("@"), sys.argv[2]
    for f in FILES:
        p = ROOT / f
        s = p.read_text(encoding="utf-8")
        new = s.replace("YOUR_USERNAME", user).replace("YOUR_NAME", name)
        if new != s:
            p.write_text(new, encoding="utf-8")
            print(f"✓ {f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
