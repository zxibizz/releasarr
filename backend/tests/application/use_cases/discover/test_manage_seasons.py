"""Tests for managing which seasons of a series hold requests."""

from __future__ import annotations

import pytest

from src.application.use_cases.discover.exceptions import (
    SeasonSelectionError,
    SeasonsUnmanageableError,
)
from src.application.use_cases.discover.manage_seasons import (
    ListRequestSeasonsUseCase,
    UpdateRequestSeasonsCommand,
    UpdateRequestSeasonsUseCase,
)
from src.application.use_cases.requests.exceptions import MediaRequestNotFoundError
from src.application.use_cases.requests.sync_sonarr import SyncSonarrMediaRequestsUseCase
from src.domain.enums import MediaType
from tests.fakes import (
    FakeMediaRequestRepository,
    FakeSonarrService,
    make_record,
    make_series_details,
)


def build_list_use_case(
    *,
    repository: FakeMediaRequestRepository,
    sonarr: FakeSonarrService,
) -> ListRequestSeasonsUseCase:
    return ListRequestSeasonsUseCase(repository=repository, sonarr_service=sonarr)


def build_update_use_case(
    *,
    repository: FakeMediaRequestRepository,
    sonarr: FakeSonarrService,
) -> UpdateRequestSeasonsUseCase:
    """Wire the real sync use case in, so the inline request creation is covered."""

    return UpdateRequestSeasonsUseCase(
        repository=repository,
        sonarr_service=sonarr,
        sync_sonarr=SyncSonarrMediaRequestsUseCase(
            repository=repository,
            sonarr_service=sonarr,
            tvdb_service=None,
        ),
    )


def series_sonarr(**kwargs: object) -> FakeSonarrService:
    return FakeSonarrService(
        catalogue={
            12: make_series_details(
                12,
                seasons={1: (10, True), 2: (8, False), 3: (6, False)},
                **kwargs,  # type: ignore[arg-type]
            )
        }
    )


@pytest.mark.asyncio
async def test_the_seasons_of_a_request_report_what_is_already_requested() -> None:
    repository = FakeMediaRequestRepository(
        {"req-1": make_record("req-1", season_number=1, sonarr_series_id=12)}
    )

    result = await build_list_use_case(
        repository=repository,
        sonarr=series_sonarr(monitor_new_seasons=True),
    ).execute("req-1")

    assert result.in_library is True
    assert result.library_id == 12
    assert result.monitor_new_seasons is True
    assert [(season.season_number, season.requested) for season in result.seasons] == [
        (1, True),
        (2, False),
        (3, False),
    ]
    assert result.seasons[0].request_id == "req-1"


@pytest.mark.asyncio
async def test_a_movie_request_has_no_seasons_to_manage() -> None:
    repository = FakeMediaRequestRepository(
        {"req-1": make_record("req-1", media_type=MediaType.MOVIE, radarr_movie_id=31)}
    )

    with pytest.raises(SeasonsUnmanageableError):
        await build_list_use_case(
            repository=repository,
            sonarr=series_sonarr(),
        ).execute("req-1")


@pytest.mark.asyncio
async def test_a_request_sonarr_has_not_seen_yet_cannot_be_managed() -> None:
    repository = FakeMediaRequestRepository({"req-1": make_record("req-1", season_number=1)})

    with pytest.raises(SeasonsUnmanageableError):
        await build_list_use_case(
            repository=repository,
            sonarr=series_sonarr(),
        ).execute("req-1")


@pytest.mark.asyncio
async def test_an_unknown_request_is_reported_as_missing() -> None:
    with pytest.raises(MediaRequestNotFoundError):
        await build_list_use_case(
            repository=FakeMediaRequestRepository(),
            sonarr=series_sonarr(),
        ).execute("missing")


@pytest.mark.asyncio
async def test_a_newly_picked_season_is_monitored_and_becomes_a_request() -> None:
    repository = FakeMediaRequestRepository(
        {"req-1": make_record("req-1", season_number=1, sonarr_series_id=12)}
    )
    sonarr = series_sonarr()

    result = await build_update_use_case(repository=repository, sonarr=sonarr).execute(
        "req-1",
        UpdateRequestSeasonsCommand(season_numbers=[1, 2]),
    )

    assert sonarr.monitored == [
        {"series_id": 12, "monitor": [2], "unmonitor": [], "monitor_new_seasons": False}
    ]
    # The request must exist by the time the call returns, not after a poll.
    assert sonarr.waited == [(12, [2])]
    seasons = {season.season_number: season.requested for season in result.seasons}
    assert seasons == {1: True, 2: True, 3: False}


@pytest.mark.asyncio
async def test_a_dropped_season_is_unmonitored_and_its_request_deleted() -> None:
    repository = FakeMediaRequestRepository(
        {
            "req-1": make_record("req-1", season_number=1, sonarr_series_id=12),
            "req-2": make_record("req-2", season_number=2, sonarr_series_id=12),
        }
    )
    sonarr = series_sonarr()

    result = await build_update_use_case(repository=repository, sonarr=sonarr).execute(
        "req-1",
        UpdateRequestSeasonsCommand(season_numbers=[1]),
    )

    assert sonarr.monitored == [
        {"series_id": 12, "monitor": [], "unmonitor": [2], "monitor_new_seasons": False}
    ]
    assert list(repository.records) == ["req-1"]
    assert [season.requested for season in result.seasons] == [True, False, False]


@pytest.mark.asyncio
async def test_adding_and_dropping_seasons_takes_one_sonarr_write() -> None:
    """Emptying the selection before refilling it is what Sonarr reads as "unmonitor me"."""

    repository = FakeMediaRequestRepository(
        {"req-1": make_record("req-1", season_number=1, sonarr_series_id=12)}
    )
    sonarr = series_sonarr()

    await build_update_use_case(repository=repository, sonarr=sonarr).execute(
        "req-1",
        UpdateRequestSeasonsCommand(season_numbers=[2, 3]),
    )

    assert sonarr.monitored == [
        {"series_id": 12, "monitor": [2, 3], "unmonitor": [1], "monitor_new_seasons": False}
    ]
    assert "req-1" not in repository.records


@pytest.mark.asyncio
async def test_an_empty_selection_withdraws_every_season_request() -> None:
    repository = FakeMediaRequestRepository(
        {"req-1": make_record("req-1", season_number=1, sonarr_series_id=12)}
    )
    sonarr = series_sonarr()

    result = await build_update_use_case(repository=repository, sonarr=sonarr).execute(
        "req-1",
        UpdateRequestSeasonsCommand(),
    )

    assert sonarr.monitored == [
        {"series_id": 12, "monitor": [], "unmonitor": [1], "monitor_new_seasons": False}
    ]
    assert repository.records == {}
    assert all(season.requested is False for season in result.seasons)


@pytest.mark.asyncio
async def test_specials_are_left_alone_by_a_selection_that_cannot_mention_them() -> None:
    repository = FakeMediaRequestRepository(
        {"req-0": make_record("req-0", season_number=0, sonarr_series_id=12)}
    )
    sonarr = series_sonarr()

    await build_update_use_case(repository=repository, sonarr=sonarr).execute(
        "req-0",
        UpdateRequestSeasonsCommand(season_numbers=[1]),
    )

    assert sonarr.monitored == [
        {"series_id": 12, "monitor": [1], "unmonitor": [], "monitor_new_seasons": False}
    ]
    assert "req-0" in repository.records


@pytest.mark.asyncio
async def test_future_seasons_can_be_asked_for_without_changing_the_selection() -> None:
    repository = FakeMediaRequestRepository(
        {"req-1": make_record("req-1", season_number=1, sonarr_series_id=12)}
    )
    sonarr = series_sonarr()

    result = await build_update_use_case(repository=repository, sonarr=sonarr).execute(
        "req-1",
        UpdateRequestSeasonsCommand(season_numbers=[1], monitor_new_seasons=True),
    )

    assert sonarr.monitored == [
        {"series_id": 12, "monitor": [], "unmonitor": [], "monitor_new_seasons": True}
    ]
    assert result.monitor_new_seasons is True
    assert sonarr.waited == []


@pytest.mark.asyncio
async def test_a_season_the_series_does_not_have_is_rejected() -> None:
    repository = FakeMediaRequestRepository(
        {"req-1": make_record("req-1", season_number=1, sonarr_series_id=12)}
    )
    sonarr = series_sonarr()

    with pytest.raises(SeasonSelectionError):
        await build_update_use_case(repository=repository, sonarr=sonarr).execute(
            "req-1",
            UpdateRequestSeasonsCommand(season_numbers=[9]),
        )

    assert sonarr.monitored == []
