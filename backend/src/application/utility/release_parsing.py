"""Best-effort season/episode extraction from release file names and paths."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass

VIDEO_EXTENSIONS = frozenset(
    {
        ".mkv",
        ".mp4",
        ".avi",
        ".mov",
        ".wmv",
        ".flv",
        ".webm",
        ".m4v",
        ".ts",
        ".m2ts",
        ".mpg",
        ".mpeg",
        ".ogm",
        ".rmvb",
    }
)

MAX_SEASON = 100
MAX_EPISODE = 999


@dataclass(frozen=True, slots=True)
class ParsedEpisode:
    """Season and episode numbers recovered from a file name."""

    season: int | None = None
    episode: int | None = None


# Ordered strongest-first: an explicit ``S01E02`` beats anything we infer later.
_SEASON_EPISODE_PATTERNS = (
    re.compile(r"(?<![a-z0-9])s(?P<season>\d{1,3})[\s._-]*e(?P<episode>\d{1,3})(?!\d)", re.I),
    re.compile(
        r"season[\s._-]*(?P<season>\d{1,3})[\s._-]*(?:episode|ep)[\s._-]*(?P<episode>\d{1,3})(?!\d)",
        re.I,
    ),
    # ``2x05``. The trailing guard keeps resolutions such as ``1920x1080`` out.
    re.compile(r"(?<![a-z0-9])(?P<season>\d{1,2})x(?P<episode>\d{1,3})(?![\dip])", re.I),
)

_SEASON_PATTERN = re.compile(
    r"(?<![a-z0-9])(?:season|series|saison|temporada|s)[\s._-]*(?P<season>\d{1,3})(?!\d)",
    re.I,
)

_EPISODE_PATTERN = re.compile(
    r"(?<![a-z0-9])(?:episode|epis[oó]dio|ep|e)[\s._-]*(?P<episode>\d{1,3})(?!\d)",
    re.I,
)

# A bare number surrounded by separators, e.g. ``Avatar - 07 [1080p].mkv``. Boundaries
# are lookarounds so two adjacent numbers are both discoverable.
_LOOSE_EPISODE_PATTERN = re.compile(
    r"(?:(?<=^)|(?<=[\s._\-\[\(]))(?P<episode>\d{1,3})(?=[\s._\-\]\)]|$)"
)

# Quality/codec/audio tokens that would otherwise be mistaken for loose episode numbers.
_JUNK_PATTERN = re.compile(
    r"(?<![a-z0-9])(?:"
    r"\d{3,4}[pi]"
    r"|\d{3,4}x\d{3,4}"
    r"|[xh][\s._-]?26[45]"
    r"|hevc|avc|xvid|divx|10bit|8bit|hdr10?|dv|sdr"
    r"|(?:19|20)\d{2}"
    r"|(?:dd\+?|ddp|ac3|eac3|aac|dts(?:[\s._-]?hd)?|truehd|atmos|flac|mp3|opus)"
    r"(?:[\s._-]?\d(?:[\s._-]?\d)?)?"
    r"|[257][\s._-]?1(?:ch)?"
    r"|web[\s._-]?dl|webrip|web|bluray|blu[\s._-]?ray|bdrip|brrip|bdremux|remux"
    r"|hdtv|dvdrip|dvd|hdrip|amzn|nf|dsnp|hmax|atvp"
    r"|repack|proper|extended|uncut|complete|multi|dual|dubbed|subbed"
    r"|v\d"
    r")(?![a-z0-9])",
    re.I,
)

_NATURAL_SPLIT_PATTERN = re.compile(r"(\d+)")


def is_video_file(name: str) -> bool:
    """Return True when the file extension looks like playable video."""

    return os.path.splitext(name)[1].lower() in VIDEO_EXTENSIONS


def natural_sort_key(value: str) -> tuple[str | int, ...]:
    """Sort key that orders ``E9`` before ``E10`` instead of lexicographically."""

    parts = _NATURAL_SPLIT_PATTERN.split(value.replace("\\", "/"))
    return tuple(int(part) if part.isdigit() else part.lower() for part in parts)


def parse_episode(name: str, path: str | None = None) -> ParsedEpisode:
    """Recover season/episode numbers from a release file.

    The file name is inspected first; when it only carries an episode number the
    enclosing directories are consulted for the season, which is how most
    multi-season packs are laid out (``Season 02/Show - 05.mkv``). ``name`` may
    itself be a relative path, as torrent file listings usually are.
    """

    segments = _segments(name)
    if not segments:
        return ParsedEpisode()

    stem = os.path.splitext(segments[-1])[0]
    directories = _segments(path)[:-1] if path else segments[:-1]

    season, episode = _match_pair(stem)
    if season is not None and episode is not None:
        return _validated(season, episode)

    if season is None:
        season, stem = _extract_season(stem)
    if season is None:
        season = _season_from_directories(directories)

    if episode is None:
        episode = _match_episode(stem)
    if episode is None and season is not None:
        episode = _match_loose_episode(stem)

    return _validated(season, episode)


def parse_seasons(path: str) -> set[int]:
    """Return every season number mentioned anywhere in a path."""

    text = path.replace("\\", "/")
    seasons = {int(match.group("season")) for match in _SEASON_PATTERN.finditer(text)}
    for pattern in _SEASON_EPISODE_PATTERNS:
        seasons.update(int(match.group("season")) for match in pattern.finditer(text))
    return {season for season in seasons if 0 <= season <= MAX_SEASON}


def _segments(path: str | None) -> list[str]:
    if not path:
        return []
    return [segment for segment in path.replace("\\", "/").split("/") if segment]


def _match_pair(stem: str) -> tuple[int | None, int | None]:
    for pattern in _SEASON_EPISODE_PATTERNS:
        match = pattern.search(stem)
        if match:
            return int(match.group("season")), int(match.group("episode"))
    return None, None


def _extract_season(stem: str) -> tuple[int | None, str]:
    """Pull the season out of a name, returning the remainder without it.

    Removing the matched text stops ``Season 2`` from later reading as episode 2.
    """

    match = _SEASON_PATTERN.search(stem)
    if match is None:
        return None, stem
    remainder = stem[: match.start()] + " " + stem[match.end() :]
    return int(match.group("season")), remainder


def _season_from_directories(directories: list[str]) -> int | None:
    for directory in reversed(directories):
        match = _SEASON_PATTERN.search(directory)
        if match:
            return int(match.group("season"))
    return None


def _match_episode(stem: str) -> int | None:
    match = _EPISODE_PATTERN.search(stem)
    return int(match.group("episode")) if match else None


def _match_loose_episode(stem: str) -> int | None:
    """Read a bare number as the episode, but only when it is unambiguous."""

    cleaned = _JUNK_PATTERN.sub(" ", stem)
    candidates = {int(match.group("episode")) for match in _LOOSE_EPISODE_PATTERN.finditer(cleaned)}
    if len(candidates) != 1:
        return None
    episode = candidates.pop()
    return episode if episode > 0 else None


def _validated(season: int | None, episode: int | None) -> ParsedEpisode:
    if season is not None and not 0 <= season <= MAX_SEASON:
        season = None
    if episode is not None and not 0 < episode <= MAX_EPISODE:
        episode = None
    return ParsedEpisode(season=season, episode=episode)


__all__ = [
    "VIDEO_EXTENSIONS",
    "ParsedEpisode",
    "is_video_file",
    "natural_sort_key",
    "parse_episode",
    "parse_seasons",
]
