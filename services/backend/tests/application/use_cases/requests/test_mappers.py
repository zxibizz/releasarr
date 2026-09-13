"""Tests for deriving the request DTOs the API serves."""

from __future__ import annotations

from src.application.use_cases.requests.dto import SeriesRequestDTO
from src.application.use_cases.requests.mappers import record_to_dto
from tests.fakes import make_record


def series_record(**overrides: int | None) -> SeriesRequestDTO:
    record = make_record("req-1", season_number=2, sonarr_series_id=12)
    record.total_episodes = overrides.get("total_episodes", 10)
    record.aired_episodes = overrides.get("aired_episodes", 8)
    record.downloaded_episodes = overrides.get("downloaded_episodes", 3)

    dto = record_to_dto(record)
    assert isinstance(dto, SeriesRequestDTO)
    return dto


def test_counts_split_the_season_into_downloaded_pending_and_unaired() -> None:
    counts = series_record()

    assert counts.episode_counts is not None
    assert counts.episode_counts.downloaded == 3
    assert counts.episode_counts.pending == 5
    assert counts.episode_counts.unaired == 2


def test_a_season_with_no_aired_episodes_reports_nothing_rather_than_zeros() -> None:
    """Rows written before the counts existed carry no aired figure at all.

    Reporting zeroes would claim the season has nothing pending, which is the
    opposite of what an unfilled season means.
    """

    assert series_record(aired_episodes=None).episode_counts is None


def test_counts_never_go_negative_when_sonarr_over_reports() -> None:
    """Sonarr can report more files than aired episodes, or more aired episodes
    than the season total. Negative badges would be worse than a clamp."""

    counts = series_record(total_episodes=5, aired_episodes=8, downloaded_episodes=9)

    assert counts.episode_counts is not None
    assert counts.episode_counts.downloaded == 9
    assert counts.episode_counts.pending == 0
    assert counts.episode_counts.unaired == 0
