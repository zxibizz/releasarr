"""Tests for season/episode extraction from release file paths."""

from __future__ import annotations

import pytest

from src.application.utility.release_parsing import (
    is_video_file,
    movie_titles,
    natural_sort_key,
    normalize_title,
    parse_episode,
    parse_seasons,
    parse_year,
)


@pytest.mark.parametrize(
    ("path", "season", "episode"),
    [
        ("Avatar.The.Last.Airbender.S01E01.1080p.BluRay.x264.mkv", 1, 1),
        ("Avatar.The.Last.Airbender.S03E20.mkv", 3, 20),
        ("Avatar - s02 e07 - The Blind Bandit.mkv", 2, 7),
        ("Show.Season 2.Episode 5.mkv", 2, 5),
        ("Show.2x05.HDTV.mkv", 2, 5),
        ("Avatar/Season 2/Avatar - 05 - The Swamp.mkv", 2, 5),
        ("Avatar/Book 1 Water/Avatar.S01E12.mkv", 1, 12),
        ("Avatar The Last Airbender Season 1/07.mkv", 1, 7),
        ("Season 3/Episode 14.mkv", 3, 14),
        # Bracketed numbering with the season only in the release title.
        ("Seihantai na Kimi to Boku S2/Seihantai na Kimi to Boku S2 [07].avi", 2, 7),
    ],
)
def test_parse_episode_recognises_common_layouts(path: str, season: int, episode: int) -> None:
    parsed = parse_episode(path)

    assert (parsed.season, parsed.episode) == (season, episode)


def test_parse_episode_prefers_the_file_name_over_the_folder() -> None:
    parsed = parse_episode("Avatar/Season 1/Avatar.S02E04.mkv")

    assert (parsed.season, parsed.episode) == (2, 4)


def test_parse_episode_takes_directories_from_the_path_when_given() -> None:
    parsed = parse_episode("05 - The Swamp.mkv", "/downloads/Avatar/Season 2/05 - The Swamp.mkv")

    assert (parsed.season, parsed.episode) == (2, 5)


def test_parse_episode_reads_a_season_pack_folder_without_an_episode() -> None:
    parsed = parse_episode("Avatar.S02.1080p.BluRay/Avatar.The.Last.Airbender.1080p.mkv")

    assert (parsed.season, parsed.episode) == (2, None)


@pytest.mark.parametrize(
    "path",
    [
        # Quality, codec and audio tokens must not read as episode numbers.
        "Avatar/Season 1/Avatar.The.Last.Airbender.1080p.1920x1080.x264.DD5.1.mkv",
        "Avatar/Season 1/Avatar.The.Last.Airbender.2005.WEB-DL.H.264.mkv",
    ],
)
def test_parse_episode_ignores_release_metadata(path: str) -> None:
    assert parse_episode(path).episode is None


def test_parse_episode_returns_nothing_for_unrelated_files() -> None:
    parsed = parse_episode("extras/behind the scenes.mkv")

    assert (parsed.season, parsed.episode) == (None, None)


def test_parse_seasons_collects_every_mentioned_season() -> None:
    assert parse_seasons("Avatar.The.Last.Airbender.S01.S02.S03.COMPLETE") == {1, 2, 3}


@pytest.mark.parametrize(
    ("name", "expected"),
    [("Show.S01E01.mkv", True), ("Show.S01E01.mp4", True), ("readme.nfo", False)],
)
def test_is_video_file(name: str, expected: bool) -> None:
    assert is_video_file(name) is expected


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("Spider-Man: No Way Home", "spidermannowayhome"),
        ("Ocean's 8", "oceans8"),
        # Non-ASCII survives, so a localized title can still be matched.
        ("Прибытие", "прибытие"),
    ],
)
def test_normalize_title_keeps_only_alphanumerics(title: str, expected: str) -> None:
    assert normalize_title(title) == expected


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("Arrival.2016.1080p.BluRay.x264.mkv", "arrival"),
        ("Iron.Man.2.2010.1080p.mkv", "ironman2"),
        ("Ocean's 8 (2018) [1080p].mkv", "oceans8"),
        # No release year, so the title is whatever precedes the first tag.
        ("The.Matrix.1080p.BluRay.mkv", "thematrix"),
        ("Прибытие.2016.1080p.mkv", "прибытие"),
    ],
)
def test_movie_titles_lead_with_the_title_without_its_tags(path: str, expected: str) -> None:
    assert movie_titles(path)[0] == expected


def test_movie_titles_fall_back_to_the_enclosing_folder() -> None:
    """Some layouts name the movie on the folder and leave the file generic."""

    assert movie_titles("Arrival (2016)/movie.mkv") == ["movie", "arrival", "arrival2016"]


def test_movie_titles_offer_both_readings_of_a_trailing_year() -> None:
    """A title may end in a year, and only the request can settle which it is."""

    assert movie_titles("Blade.Runner.2049.1080p.BluRay.mkv") == ["bladerunner", "bladerunner2049"]
    assert movie_titles("Blade.Runner.2049.2017.1080p.mkv")[0] == "bladerunner2049"


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("Arrival.2016.1080p.mkv", 2016),
        # The release year comes after a title that carries one of its own.
        ("Blade.Runner.2049.2017.1080p.mkv", 2017),
        ("Arrival (2016)/movie.mkv", 2016),
        ("Arrival.1080p.mkv", None),
    ],
)
def test_parse_year_reads_the_release_year(path: str, expected: int | None) -> None:
    assert parse_year(path) == expected


def test_natural_sort_key_orders_episode_nine_before_ten() -> None:
    names = ["Show.S01E10.mkv", "Show.S01E9.mkv", "Show.S01E2.mkv"]

    assert sorted(names, key=natural_sort_key) == [
        "Show.S01E2.mkv",
        "Show.S01E9.mkv",
        "Show.S01E10.mkv",
    ]
