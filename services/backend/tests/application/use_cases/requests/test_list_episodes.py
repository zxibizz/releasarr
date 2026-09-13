"""Tests for the episode list behind a series request."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from src.application.interfaces.sonarr import SonarrEpisode
from src.application.use_cases.discover.exceptions import SeasonsUnmanageableError
from src.application.use_cases.requests.exceptions import MediaRequestNotFoundError
from src.application.use_cases.requests.list_episodes import ListRequestEpisodesUseCase
from src.domain.enums import EpisodeStatus, MediaType
from tests.fakes import FakeMediaRequestRepository, FakeSonarrService, make_record

NOW = datetime.now(UTC)
AIRED = NOW - timedelta(days=7)
TO_COME = NOW + timedelta(days=7)


def build_use_case(
    *,
    repository: FakeMediaRequestRepository,
    sonarr: FakeSonarrService,
) -> ListRequestEpisodesUseCase:
    return ListRequestEpisodesUseCase(repository=repository, sonarr_service=sonarr)


def episode(
    number: int,
    *,
    season: int = 2,
    title: str = "An Episode",
    air_date: datetime | None = AIRED,
    has_file: bool = False,
    file_size: int | None = None,
) -> SonarrEpisode:
    return SonarrEpisode(
        id=season * 100 + number,
        season_number=season,
        episode_number=number,
        title=title,
        air_date=air_date,
        has_file=has_file,
        file_size=file_size,
    )


@pytest.mark.asyncio
async def test_only_the_episodes_of_the_requested_season_are_listed() -> None:
    """A request covers one season, and Sonarr answers for the whole series."""

    repository = FakeMediaRequestRepository(
        records={"req-1": make_record("req-1", season_number=2, sonarr_series_id=12)}
    )
    sonarr = FakeSonarrService(
        episodes={
            12: [
                episode(1, season=1),
                episode(2, season=2),
                episode(1, season=2),
                episode(1, season=3),
            ]
        }
    )

    result = await build_use_case(repository=repository, sonarr=sonarr).execute("req-1")

    assert result.season_number == 2
    # In episode order, however Sonarr happened to return them.
    assert [item.episode_number for item in result.episodes] == [1, 2]


@pytest.mark.asyncio
async def test_an_episode_is_downloaded_missing_or_unaired() -> None:
    repository = FakeMediaRequestRepository(
        records={"req-1": make_record("req-1", season_number=2, sonarr_series_id=12)}
    )
    sonarr = FakeSonarrService(
        episodes={
            12: [
                episode(1, has_file=True),
                episode(2),
                episode(3, air_date=TO_COME),
                episode(4, air_date=None),
            ]
        }
    )

    result = await build_use_case(repository=repository, sonarr=sonarr).execute("req-1")

    assert [item.status for item in result.episodes] == [
        EpisodeStatus.DOWNLOADED,
        EpisodeStatus.MISSING,
        EpisodeStatus.UNAIRED,
        # No date at all is nothing to be late on, so it reads as unaired too.
        EpisodeStatus.UNAIRED,
    ]


@pytest.mark.asyncio
async def test_a_held_file_outranks_an_air_date_still_to_come() -> None:
    """A premiere put out early must not be reported as nothing to see yet."""

    repository = FakeMediaRequestRepository(
        records={"req-1": make_record("req-1", season_number=2, sonarr_series_id=12)}
    )
    sonarr = FakeSonarrService(episodes={12: [episode(1, air_date=TO_COME, has_file=True)]})

    result = await build_use_case(repository=repository, sonarr=sonarr).execute("req-1")

    assert result.episodes[0].status is EpisodeStatus.DOWNLOADED


@pytest.mark.asyncio
async def test_the_title_air_date_and_size_come_through() -> None:
    repository = FakeMediaRequestRepository(
        records={"req-1": make_record("req-1", season_number=2, sonarr_series_id=12)}
    )
    sonarr = FakeSonarrService(
        episodes={
            12: [
                episode(1, title="Pilot", air_date=AIRED, has_file=True, file_size=1_073_741_824),
                episode(2),
            ]
        }
    )

    result = await build_use_case(repository=repository, sonarr=sonarr).execute("req-1")

    first, second = result.episodes
    assert (first.title, first.air_date, first.file_size) == ("Pilot", AIRED, 1_073_741_824)
    # Nothing on disk to report for an episode with no file.
    assert second.file_size is None


@pytest.mark.asyncio
async def test_a_season_sonarr_has_no_episodes_for_comes_back_empty() -> None:
    repository = FakeMediaRequestRepository(
        records={"req-1": make_record("req-1", season_number=9, sonarr_series_id=12)}
    )
    sonarr = FakeSonarrService(episodes={12: [episode(1, season=1)]})

    result = await build_use_case(repository=repository, sonarr=sonarr).execute("req-1")

    assert (result.season_number, result.episodes) == (9, [])


@pytest.mark.asyncio
async def test_a_movie_request_has_no_episodes_to_list() -> None:
    repository = FakeMediaRequestRepository(
        records={
            "req-1": make_record("req-1", media_type=MediaType.MOVIE, radarr_movie_id=31),
        }
    )

    with pytest.raises(SeasonsUnmanageableError):
        await build_use_case(repository=repository, sonarr=FakeSonarrService()).execute("req-1")


@pytest.mark.asyncio
async def test_a_request_sonarr_has_not_linked_yet_has_no_episodes_to_list() -> None:
    repository = FakeMediaRequestRepository(
        records={"req-1": make_record("req-1", season_number=2)}
    )

    with pytest.raises(SeasonsUnmanageableError):
        await build_use_case(repository=repository, sonarr=FakeSonarrService()).execute("req-1")


@pytest.mark.asyncio
async def test_an_unknown_request_is_reported_as_missing() -> None:
    with pytest.raises(MediaRequestNotFoundError):
        await build_use_case(
            repository=FakeMediaRequestRepository(),
            sonarr=FakeSonarrService(),
        ).execute("nope")
