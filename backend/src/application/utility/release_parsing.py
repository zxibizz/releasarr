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

# Quality/codec/audio/source tokens that follow the title in a release name.
_RELEASE_TAGS = (
    r"\d{3,4}[pi]"
    r"|\d{3,4}x\d{3,4}"
    r"|[xh][\s._-]?26[45]"
    r"|hevc|avc|xvid|divx|10bit|8bit|hdr10?|dv|sdr"
    r"|(?:dd\+?|ddp|ac3|eac3|aac|dts(?:[\s._-]?hd)?|truehd|atmos|flac|mp3|opus)"
    r"(?:[\s._-]?\d(?:[\s._-]?\d)?)?"
    r"|[257][\s._-]?1(?:ch)?"
    r"|web[\s._-]?dl|webrip|web|bluray|blu[\s._-]?ray|bdrip|brrip|bdremux|remux"
    r"|hdtv|dvdrip|dvd|hdrip|amzn|nf|dsnp|hmax|atvp"
    r"|repack|proper|extended|uncut|complete|multi|dual|dubbed|subbed"
    r"|v\d"
)

_TAG_PATTERN = re.compile(rf"(?<![a-z0-9])(?:{_RELEASE_TAGS})(?![a-z0-9])", re.I)

# Everything above plus years, which would otherwise read as loose episode numbers.
_JUNK_PATTERN = re.compile(
    rf"(?<![a-z0-9])(?:{_RELEASE_TAGS}|(?:19|20)\d{{2}})(?![a-z0-9])",
    re.I,
)

_NATURAL_SPLIT_PATTERN = re.compile(r"(\d+)")

_YEAR_PATTERN = re.compile(r"(?<!\d)(?P<year>(?:19|20)\d{2})(?!\d)")


def is_video_file(name: str) -> bool:
    """Return True when the file extension looks like playable video."""

    return os.path.splitext(name)[1].lower() in VIDEO_EXTENSIONS


def normalize_title(value: str) -> str:
    """Reduce a title to the comparable form Radarr calls a clean title.

    Punctuation, separators and case carry no meaning when comparing a release
    name against a request, so only alphanumerics survive. ``str.isalnum`` rather
    than an ASCII character class, because a request's title may be localized and
    the release named to match.
    """

    return "".join(character for character in value.lower() if character.isalnum())


def movie_titles(name: str, path: str | None = None) -> list[str]:
    """Normalized titles a movie file may be named after, most specific first.

    A release name is its title followed by tags, so the title is whatever
    precedes them. Where the year sits is ambiguous - a title may end in one
    ("Blade Runner 2049") - so both readings are offered and the caller takes
    whichever one it recognises. Enclosing folders come last, for the layouts
    that name the movie there and leave the file itself unhelpful.
    """

    segments = _segments(path or name)
    if not segments:
        return []

    sources = [os.path.splitext(segments[-1])[0], *reversed(segments[:-1])]
    titles: list[str] = []
    for source in sources:
        for candidate in _title_candidates(source):
            title = normalize_title(candidate)
            if title and title not in titles:
                titles.append(title)
    return titles


def parse_year(name: str, path: str | None = None) -> int | None:
    """Recover the release year from a file name, falling back to its folders.

    The common movie layout puts the year on the folder rather than every file
    inside it (``Movie (2019)/movie.mkv``).
    """

    segments = _segments(name)
    if not segments:
        return None

    year = _match_year(os.path.splitext(segments[-1])[0])
    if year is not None:
        return year

    directories = _segments(path)[:-1] if path else segments[:-1]
    for directory in reversed(directories):
        year = _match_year(directory)
        if year is not None:
            return year
    return None


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


def _title_candidates(text: str) -> list[str]:
    candidates: list[str] = []

    years = list(_YEAR_PATTERN.finditer(text))
    if years:
        # The release year is the last one, so anything before it is the title.
        candidates.append(text[: years[-1].start()])

    # And the reading where the trailing year belongs to the title instead.
    tag = _TAG_PATTERN.search(text)
    candidates.append(text[: tag.start()] if tag else text)

    return candidates


def _match_year(text: str) -> int | None:
    # Last wins: a title may itself carry a year ("Blade Runner 2049"), and the
    # release year is appended after it.
    matches = _YEAR_PATTERN.findall(text)
    return int(matches[-1]) if matches else None


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
    "movie_titles",
    "natural_sort_key",
    "normalize_title",
    "parse_episode",
    "parse_seasons",
    "parse_year",
]
