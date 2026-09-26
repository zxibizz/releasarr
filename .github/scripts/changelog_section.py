#!/usr/bin/env python3
"""Print the CHANGELOG.md section for one version, for use as release notes.

Usage:
    changelog_section.py v1.2.3
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def section(version: str) -> str:
    lines = (ROOT / "CHANGELOG.md").read_text().splitlines()

    # A prerelease has no heading of its own; fall back to the release it leads to.
    candidates = [version]
    if "-" in version:
        candidates.append(version.split("-", 1)[0])

    for candidate in candidates:
        heading = f"## [{candidate}]"
        start = next((i for i, line in enumerate(lines) if line.startswith(heading)), None)
        if start is None:
            continue
        end = next(
            (i for i, line in enumerate(lines[start + 1 :], start + 1) if line.startswith("## ")),
            len(lines),
        )
        body = lines[start + 1 : end]
        # The link references at the bottom belong to the file, not to the last section.
        while body and (not body[-1].strip() or body[-1].startswith("[")):
            body.pop()
        return "\n".join(body).strip()

    wanted = " or ".join(f"'## [{c}]'" for c in candidates)
    raise SystemExit(f"no {wanted} section in CHANGELOG.md")


def main(argv: list[str]) -> int:
    if not argv:
        raise SystemExit("usage: changelog_section.py <tag>")
    print(section(argv[0].removeprefix("refs/tags/").removeprefix("v")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
