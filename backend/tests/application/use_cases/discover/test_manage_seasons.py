"""Tests for managing which seasons of a series Sonarr monitors."""

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


def series_sonarr(
    seasons: dict[int, tuple[int, bool]] | None = None,
    **kwargs: object,
) -> FakeSonarrService:
    return FakeSonarrService(
        catalogue={
            12: make_series_details(
                12,
                seasons=seasons or {1: (10, True), 2: (8, False), 3: (6, False)},
                **kwargs,  # type: ignore[arg-type]
            )
        }
    )


@pytest.mark.asyncio
async def test_the_seasons_of_a_request_report_sonarrs_own_monitoring() -> None:
    repository = FakeMediaRequestRepository(
        {"req-1": make_record("req-1", season_number=1, sonarr_series_id=12)}
    )

    result = await build_list_use_case(
        repository=repository,
        sonarr=series_sonarr(monitored=True, monitor_new_seasons=True),
    ).execute("req-1")

    assert result.in_library is True
    assert result.library_id == 12
    assert result.monitored is True
    assert result.monitor_new_seasons is True
    assert [(season.season_number, season.monitored) for season in result.seasons] == [
        (1, True),
        (2, False),
        (3, False),
    ]
    assert result.seasons[0].request_id == "req-1"


@pytest.mark.asyncio
async def test_a_monitored_season_with_no_request_is_still_reported_monitored() -> None:
    """A season Sonarr already holds in full never becomes a request of ours.

    Reporting those as unmonitored is what would let the manager offer them
    unticked and then withdraw them from Sonarr on the next save.
    """

    repository = FakeMediaRequestRepository(
        {"req-1": make_record("req-1", season_number=3, sonarr_series_id=12)}
    )

    result = await build_list_use_case(
        repository=repository,
        sonarr=series_sonarr({1: (10, True), 2: (8, True), 3: (6, True)}),
    ).execute("req-1")

    assert [(season.monitored, season.requested) for season in result.seasons] == [
        (True, False),
        (True, False),
        (True, True),
    ]


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
        {
            "series_id": 12,
            "monitor": [2],
            "unmonitor": [],
            "monitored": None,
            "monitor_new_seasons": False,
        }
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
    sonarr = series_sonarr({1: (10, True), 2: (8, True), 3: (6, False)})

    result = await build_update_use_case(repository=repository, sonarr=sonarr).execute(
        "req-1",
        UpdateRequestSeasonsCommand(season_numbers=[1]),
    )

    assert sonarr.monitored == [
        {
            "series_id": 12,
            "monitor": [],
            "unmonitor": [2],
            "monitored": None,
            "monitor_new_seasons": False,
        }
    ]
    assert list(repository.records) == ["req-1"]
    assert [season.monitored for season in result.seasons] == [True, False, False]


@pytest.mark.asyncio
async def test_a_season_monitored_without_a_request_is_left_where_it_is() -> None:
    """The selection is diffed against Sonarr, so an untouched tick does nothing.

    Diffed against our requests instead, season 2 would read as newly picked and
    be synced into a request it has no business having.
    """

    repository = FakeMediaRequestRepository(
        {"req-1": make_record("req-1", season_number=1, sonarr_series_id=12)}
    )
    sonarr = series_sonarr({1: (10, True), 2: (8, True), 3: (6, False)})

    await build_update_use_case(repository=repository, sonarr=sonarr).execute(
        "req-1",
        UpdateRequestSeasonsCommand(season_numbers=[1, 2]),
    )

    assert sonarr.monitored == [
        {
            "series_id": 12,
            "monitor": [],
            "unmonitor": [],
            "monitored": None,
            "monitor_new_seasons": False,
        }
    ]
    assert sonarr.waited == []
    assert list(repository.records) == ["req-1"]


@pytest.mark.asyncio
async def test_dropping_a_season_that_never_had_a_request_just_unmonitors_it() -> None:
    repository = FakeMediaRequestRepository(
        {"req-1": make_record("req-1", season_number=1, sonarr_series_id=12)}
    )
    sonarr = series_sonarr({1: (10, True), 2: (8, True), 3: (6, False)})

    await build_update_use_case(repository=repository, sonarr=sonarr).execute(
        "req-1",
        UpdateRequestSeasonsCommand(season_numbers=[1]),
    )

    assert sonarr.monitored == [
        {
            "series_id": 12,
            "monitor": [],
            "unmonitor": [2],
            "monitored": None,
            "monitor_new_seasons": False,
        }
    ]
    assert list(repository.records) == ["req-1"]


@pytest.mark.asyncio
async def test_the_series_flag_is_saved_to_sonarr_as_it_was_left() -> None:
    repository = FakeMediaRequestRepository(
        {"req-1": make_record("req-1", season_number=1, sonarr_series_id=12)}
    )
    sonarr = series_sonarr(monitored=True)

    result = await build_update_use_case(repository=repository, sonarr=sonarr).execute(
        "req-1",
        UpdateRequestSeasonsCommand(season_numbers=[1], monitored=False),
    )

    assert sonarr.monitored[0]["monitored"] is False
    assert result.monitored is False


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
        {
            "series_id": 12,
            "monitor": [2, 3],
            "unmonitor": [1],
            "monitored": None,
            "monitor_new_seasons": False,
        }
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
        {
            "series_id": 12,
            "monitor": [],
            "unmonitor": [1],
            "monitored": None,
            "monitor_new_seasons": False,
        }
    ]
    assert repository.records == {}
    assert all(season.monitored is False for season in result.seasons)


@pytest.mark.asyncio
async def test_specials_are_left_alone_by_a_selection_that_cannot_mention_them() -> None:
    repository = FakeMediaRequestRepository(
        {"req-0": make_record("req-0", season_number=0, sonarr_series_id=12)}
    )
    sonarr = series_sonarr({0: (4, True), 1: (10, False), 2: (8, False), 3: (6, False)})

    await build_update_use_case(repository=repository, sonarr=sonarr).execute(
        "req-0",
        UpdateRequestSeasonsCommand(season_numbers=[1]),
    )

    # Season 0 is monitored and left out of the selection, yet is not withdrawn.
    assert sonarr.monitored == [
        {
            "series_id": 12,
            "monitor": [1],
            "unmonitor": [],
            "monitored": None,
            "monitor_new_seasons": False,
        }
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
        {
            "series_id": 12,
            "monitor": [],
            "unmonitor": [],
            "monitored": None,
            "monitor_new_seasons": True,
        }
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
