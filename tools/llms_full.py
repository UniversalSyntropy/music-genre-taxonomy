#!/usr/bin/env python3
"""Join the documents into llms-full.txt.

Usage: python3 tools/llms_full.py [--check]
Writes llms-full.txt in the repo root. With --check, write nothing and exit 1
if the file is missing or stale. Needs only the standard library.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FILES = [
    "README.md",
    "docs/data-guide.md",
    "docs/sources.md",
    "docs/viewer.md",
    "DISCLAIMER.md",
    "CONTRIBUTING.md",
    "CHANGELOG.md",
]
OUT = ROOT / "llms-full.txt"


def build() -> str:
    parts = [
        "# Music Genre Taxonomy: full text\n\n"
        "This file joins the documents of https://github.com/UniversalSyntropy/music-genre-taxonomy "
        "in one text. Relative links point to files in that repo. The index is llms.txt.\n"
    ]
    for rel in FILES:
        text = (ROOT / rel).read_text(encoding="utf-8").rstrip("\n")
        parts.append(f"\n---\n\nFILE: {rel}\n\n{text}\n")
    return "".join(parts)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="fail if llms-full.txt is stale")
    a = ap.parse_args()
    want = build()
    if a.check:
        have = OUT.read_text(encoding="utf-8") if OUT.exists() else None
        if have != want:
            print("FAIL: llms-full.txt is missing or stale. Run: python3 tools/llms_full.py")
            return 1
        print("OK: llms-full.txt is current.")
        return 0
    OUT.write_text(want, encoding="utf-8", newline="\n")
    print(f"Wrote {OUT.name} ({len(want)} characters, {len(FILES)} files).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
