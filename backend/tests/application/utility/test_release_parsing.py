"""Tests for season/episode extraction from release file paths."""

from __future__ import annotations

import pytest

from src.application.utility.release_parsing import (
    is_video_file,
    natural_sort_key,
    parse_episode,
    parse_seasons,
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


def test_natural_sort_key_orders_episode_nine_before_ten() -> None:
    names = ["Show.S01E10.mkv", "Show.S01E9.mkv", "Show.S01E2.mkv"]

    assert sorted(names, key=natural_sort_key) == [
        "Show.S01E2.mkv",
        "Show.S01E9.mkv",
        "Show.S01E10.mkv",
    ]
