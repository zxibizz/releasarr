#!/usr/bin/env python3
"""Set the project version everywhere at once, and open a CHANGELOG section.

The version is mirrored in files that cannot import each other, so a release is
the one moment they are all allowed to change -- and the one moment they can
silently drift. `check_version.py` catches the drift; this opens the release
properly so there is none.

Usage:
    bump_version.py 1.2.3

Writes files only. Committing and tagging stay deliberate, manual acts: review
the CHANGELOG section this opens, commit, then tag that commit.

Prereleases need no bump. `check_version.py` accepts v1.2.3-rc1 against sources
that say 1.2.3, so cut the release candidate from the bumped commit as-is.
"""

from __future__ import annotations

import datetime as dt
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

PYPROJECT = Path("services/backend/pyproject.toml")
INIT = Path("services/backend/src/__init__.py")
# Embeds the project version; left stale, `uv sync --locked` fails.
UV_LOCK = Path("services/backend/uv.lock")
OPENAPI = Path("openapi.yaml")
PACKAGE_JSON = Path("services/frontend/package.json")
PACKAGE_LOCK = Path("services/frontend/package-lock.json")
CHANGELOG = Path("CHANGELOG.md")
# Mirrors check_version.IMAGE_TAG_FILES.
IMAGE_TAG_FILES = (
    Path("README.md"),
    Path("docs/upgrading.md"),
    Path("compose.example.yaml"),
    Path("compose.split.example.yaml"),
    Path(".github/ISSUE_TEMPLATE/bug_report.yml"),
)


def bump_image_tags(version: str) -> None:
    for path in IMAGE_TAG_FILES:
        target = ROOT / path
        text = re.sub(
            r"(ghcr\.io/zxibizz/releasarr:)\d+\.\d+\.\d+\b",
            rf"\g<1>{version}",
            target.read_text(),
        )
        target.write_text(text)


def _sub_once(path: Path, pattern: str, replacement: str) -> None:
    """Rewrite the first match of `pattern` in `path`."""
    target = ROOT / path
    text = target.read_text()
    new_text, count = re.subn(pattern, replacement, text, count=1, flags=re.MULTILINE)
    if count != 1:
        raise SystemExit(f"no line matching {pattern!r} in {path}")
    target.write_text(new_text)


def bump_lock(version: str) -> None:
    """Rewrite both root version sites in package-lock.json.

    Line-scoped rather than a JSON round-trip: npm's formatting is not
    reproducible from `json.dumps`, and a reformatted lockfile would bury the one
    line that actually changed.
    """
    target = ROOT / PACKAGE_LOCK
    lines = target.read_text().splitlines(keepends=True)

    top = re.compile(r'^(  "version": ")[^"]+(",?)$')
    nested = re.compile(r'^(      "version": ")[^"]+(",?)$')

    done_top = False
    in_root_package = False
    done_nested = False

    for i, line in enumerate(lines):
        stripped = line.rstrip("\n")
        if not done_top and (found := top.match(stripped)):
            lines[i] = f"{found[1]}{version}{found[2]}\n"
            done_top = True
        elif stripped == '    "": {':
            in_root_package = True
        elif in_root_package and not done_nested and (found := nested.match(stripped)):
            lines[i] = f"{found[1]}{version}{found[2]}\n"
            done_nested = True

    if not (done_top and done_nested):
        raise SystemExit(f"could not locate both root version keys in {PACKAGE_LOCK}")
    target.write_text("".join(lines))


def open_changelog_section(version: str, today: str) -> None:
    """Retitle `## [Unreleased]` as the new release and move the link refs."""
    target = ROOT / CHANGELOG
    text = target.read_text()

    if f"\n## [{version}]" in text:
        raise SystemExit(f"CHANGELOG.md already has a '## [{version}]' section")

    text, count = re.subn(
        r"^## \[Unreleased\]$",
        f"## [Unreleased]\n\n## [{version}] - {today}",
        text,
        count=1,
        flags=re.MULTILINE,
    )
    if count != 1:
        raise SystemExit("no '## [Unreleased]' heading in CHANGELOG.md")

    ref = re.search(
        r"^\[Unreleased\]: (?P<base>https://\S+?)/compare/v[^.]+(?:\.[^.]+)*\.\.\.HEAD$",
        text,
        re.MULTILINE,
    )
    if ref is None:
        raise SystemExit("no '[Unreleased]: .../compare/vX.Y.Z...HEAD' link in CHANGELOG.md")
    base = ref.group("base")
    text = text.replace(
        ref.group(0),
        f"[Unreleased]: {base}/compare/v{version}...HEAD\n"
        f"[{version}]: {base}/releases/tag/v{version}",
        1,
    )
    target.write_text(text)


def dirty_paths() -> list[str]:
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return []  # Not a checkout, or no git. Not our problem to enforce.
    return [line[3:] for line in result.stdout.splitlines()]


def main(argv: list[str]) -> int:
    args = [a for a in argv if not a.startswith("-")]
    force = "--force" in argv
    if len(args) != 1 or not re.fullmatch(r"\d+\.\d+\.\d+", args[0]):
        raise SystemExit("usage: bump_version.py X.Y.Z [--force]")
    version = args[0]

    if not force and (dirty := dirty_paths()):
        print("working tree is not clean; the bump should be its own commit:", file=sys.stderr)
        for path in dirty:
            print(f"  {path}", file=sys.stderr)
        print("re-run with --force to bump anyway", file=sys.stderr)
        return 1

    _sub_once(PYPROJECT, r'^version = "[^"]+"', f'version = "{version}"')
    _sub_once(INIT, r'^__version__ = "[^"]+"', f'__version__ = "{version}"')
    _sub_once(
        UV_LOCK,
        r'^(name = "releasarr-backend"\nversion = ")[^"]+(")',
        rf"\g<1>{version}\g<2>",
    )
    _sub_once(OPENAPI, r"^(info:\n(?:  .*\n)*?  version: )\S+$", rf"\g<1>{version}")
    _sub_once(PACKAGE_JSON, r'^(  "version": ")[^"]+(")', rf"\g<1>{version}\g<2>")
    bump_lock(version)
    bump_image_tags(version)
    open_changelog_section(version, dt.date.today().isoformat())

    for path in (
        PYPROJECT,
        INIT,
        UV_LOCK,
        OPENAPI,
        PACKAGE_JSON,
        PACKAGE_LOCK,
        *IMAGE_TAG_FILES,
        CHANGELOG,
    ):
        print(f"  updated {path}")

    # The guard CI runs, against the tag this bump is for.
    verify = subprocess.run(
        [sys.executable, str(HERE / "check_version.py"), f"v{version}"],
        cwd=ROOT,
    )
    if verify.returncode != 0:
        return verify.returncode

    print(f"\nreview the '## [{version}]' section, then:")
    print(f'  git commit -am "Release v{version}"')
    print(f"  git tag -a v{version} -m v{version} && git push origin master v{version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
