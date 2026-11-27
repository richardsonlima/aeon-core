#!/usr/bin/env python3
"""Print the Keep a Changelog section for one version.

Usage: release_notes.py VERSION [CHANGELOG]

VERSION may carry a leading "v". Exits 1 if the section is missing or empty.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


def extract(text: str, version: str) -> str | None:
    version = version.removeprefix("v")
    heading = re.compile(r"^##\s+\[?v?" + re.escape(version) + r"\]?(\s|$)", re.IGNORECASE)
    any_heading = re.compile(r"^##\s")
    lines = text.splitlines()
    start = next((i for i, line in enumerate(lines) if heading.match(line)), None)
    if start is None:
        return None
    end = next((j for j in range(start + 1, len(lines)) if any_heading.match(lines[j])), len(lines))
    body = [line for line in lines[start + 1 : end]]
    # drop trailing link reference definitions, e.g. "[0.5.0]: https://..."
    while body and (not body[-1].strip() or re.match(r"^\[[^\]]+\]:\s", body[-1])):
        body.pop()
    notes = "\n".join(body).strip()
    return notes or None


def main(argv: list[str]) -> int:
    if len(argv) not in (2, 3):
        print(__doc__, file=sys.stderr)
        return 2
    path = Path(argv[2]) if len(argv) == 3 else Path("CHANGELOG.md")
    if not path.is_file():
        print(f"release_notes: {path} not found", file=sys.stderr)
        return 1
    notes = extract(path.read_text(encoding="utf-8"), argv[1])
    if notes is None:
        print(f"release_notes: no non-empty section for {argv[1]} in {path}", file=sys.stderr)
        return 1
    print(notes)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
