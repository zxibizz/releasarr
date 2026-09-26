#!/usr/bin/env python3
"""Assert the version mirrors agree, and optionally match a release tag.

The version is declared in several files because none of them can import the
others: the backend package, the frontend bundle, the API contract and the lock
files. This is the guard that keeps them from drifting. `bump_version.py` moves
them all at once.

Usage:
    check_version.py            # the files agree
    check_version.py v1.2.3     # ...and match this git tag

A prerelease tag matches the release it is a candidate for, so v1.2.3-rc1 is
accepted while the sources still say 1.2.3.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# Docs that pin the published image; a stale tag there sends users to an old release.
IMAGE_TAG_FILES = (
    Path("README.md"),
    Path("docs/upgrading.md"),
    Path("compose.example.yaml"),
    Path("compose.split.example.yaml"),
    Path(".github/ISSUE_TEMPLATE/bug_report.yml"),
)
IMAGE_TAG = r"ghcr\.io/zxibizz/releasarr:(\d+\.\d+\.\d+)\b"


def _match(path: Path, pattern: str) -> str:
    text = (ROOT / path).read_text()
    found = re.search(pattern, text, re.MULTILINE)
    if found is None:
        raise SystemExit(f"no version matching {pattern!r} in {path}")
    return found.group(1)


def from_pyproject() -> str:
    # Regex rather than tomllib so this runs under any python3, not just 3.11+.
    return _match(Path("services/backend/pyproject.toml"), r'^version = "([^"]+)"')


def from_init() -> str:
    return _match(Path("services/backend/src/__init__.py"), r'^__version__ = "([^"]+)"')


def from_uv_lock() -> str:
    return _match(
        Path("services/backend/uv.lock"), r'^name = "releasarr-backend"\nversion = "([^"]+)"'
    )


def from_openapi() -> str:
    return _match(Path("openapi.yaml"), r"^info:\n(?:  .*\n)*?  version: (\S+)$")


def from_package_json() -> str:
    data = json.loads((ROOT / "services/frontend/package.json").read_text())
    version = data["version"]
    assert isinstance(version, str)
    return version


def from_package_lock() -> str:
    # npm records the root version twice and `npm ci` trusts the lockfile, so a
    # half-bumped lock is a real failure, not a cosmetic one.
    data = json.loads((ROOT / "services/frontend/package-lock.json").read_text())
    versions = {data["version"], data["packages"][""]["version"]}
    if len(versions) != 1:
        raise SystemExit(f"package-lock.json disagrees with itself: {sorted(versions)}")
    version = versions.pop()
    assert isinstance(version, str)
    return version


def image_tags() -> dict[str, str]:
    found: dict[str, str] = {}
    for path in IMAGE_TAG_FILES:
        for index, tag in enumerate(re.findall(IMAGE_TAG, (ROOT / path).read_text())):
            found[f"{path} (image tag {index + 1})"] = tag
    return found


def main(argv: list[str]) -> int:
    found = {
        "services/backend/pyproject.toml": from_pyproject(),
        "services/backend/src/__init__.py": from_init(),
        "services/backend/uv.lock": from_uv_lock(),
        "openapi.yaml": from_openapi(),
        "services/frontend/package.json": from_package_json(),
        "services/frontend/package-lock.json": from_package_lock(),
        **image_tags(),
    }

    if argv:
        tag = argv[0].removeprefix("refs/tags/").removeprefix("v")
        found["git tag"] = tag.split("-", 1)[0]

    distinct = set(found.values())
    if len(distinct) == 1:
        print(f"version {distinct.pop()} is consistent across {len(found)} sources")
        return 0

    print("version mismatch:", file=sys.stderr)
    for source, version in found.items():
        print(f"  {version:<12} {source}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
