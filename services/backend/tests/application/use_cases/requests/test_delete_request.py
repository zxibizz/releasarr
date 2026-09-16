"""Tests for removing a media request and the monitoring behind it."""

from __future__ import annotations

import pytest

from src.application.use_cases.requests.delete_request import DeleteMediaRequestUseCase
from src.application.use_cases.requests.exceptions import MediaRequestNotFoundError
from src.domain.enums import MediaType
from tests.fakes import (
    FakeMediaRequestRepository,
    FakeRadarrService,
    FakeSonarrService,
    make_movie_details,
    make_record,
    make_series_details,
)


def build_use_case(
    *,
    repository: FakeMediaRequestRepository,
    sonarr: FakeSonarrService | None = None,
    radarr: FakeRadarrService | None = None,
) -> DeleteMediaRequestUseCase:
    return DeleteMediaRequestUseCase(
        repository=repository,
        sonarr_service=sonarr or FakeSonarrService(),
        radarr_service=radarr or FakeRadarrService(),
    )


def series_sonarr(**kwargs: object) -> FakeSonarrService:
    return FakeSonarrService(catalogue={12: make_series_details(12, **kwargs)})  # type: ignore[arg-type]


def movie_radarr(**kwargs: object) -> FakeRadarrService:
    return FakeRadarrService(catalogue={31: make_movie_details(31, **kwargs)})  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_removing_a_season_request_unmonitors_it_in_sonarr() -> None:
    """Left monitored, the next sync would hand the request straight back."""

    record = make_record("req-1", season_number=2, sonarr_series_id=12)
    repository = FakeMediaRequestRepository({record.id: record})
    sonarr = series_sonarr(seasons={2: (8, True), 3: (6, False)}, downloaded_seasons=[3])

    await build_use_case(repository=repository, sonarr=sonarr).execute("req-1")

    # The new-season flag is left unstated, removing one request being no
    # verdict on whether future seasons are still wanted.
    assert sonarr.monitored == [
        {"series_id": 12, "monitor": [], "unmonitor": [2], "monitor_new_seasons": None}
    ]
    assert repository.records == {}


@pytest.mark.asyncio
async def test_removing_the_last_season_request_takes_an_empty_series_with_it() -> None:
    """Nothing monitored and nothing on disk leaves only a library entry behind."""

    record = make_record("req-1", season_number=2, sonarr_series_id=12)
    repository = FakeMediaRequestRepository({record.id: record})
    sonarr = series_sonarr(seasons={1: (10, False), 2: (8, True)})

    await build_use_case(repository=repository, sonarr=sonarr).execute("req-1")

    assert sonarr.deleted == [12]


@pytest.mark.asyncio
async def test_a_series_holding_an_episode_file_is_only_unmonitored() -> None:
    """The entry a file on disk would be imported through is worth keeping."""

    record = make_record("req-1", season_number=2, sonarr_series_id=12)
    repository = FakeMediaRequestRepository({record.id: record})
    sonarr = series_sonarr(
        seasons={1: (10, False), 2: (8, True)},
        downloaded_seasons=[1],
    )

    await build_use_case(repository=repository, sonarr=sonarr).execute("req-1")

    assert sonarr.deleted == []


@pytest.mark.asyncio
async def test_a_series_another_request_still_names_is_kept() -> None:
    """Deleting one season of two must not orphan the request left behind."""

    repository = FakeMediaRequestRepository(
        {
            "req-1": make_record("req-1", season_number=2, sonarr_series_id=12),
            "req-2": make_record("req-2", season_number=3, sonarr_series_id=12),
        }
    )
    sonarr = series_sonarr(seasons={1: (10, False), 2: (8, True), 3: (6, False)})

    await build_use_case(repository=repository, sonarr=sonarr).execute("req-1")

    assert sonarr.deleted == []
    assert set(repository.records) == {"req-2"}


@pytest.mark.asyncio
async def test_a_series_still_wanted_for_future_seasons_is_kept() -> None:
    """Sonarr monitoring seasons yet to air is a series wanting something."""

    record = make_record("req-1", season_number=2, sonarr_series_id=12)
    repository = FakeMediaRequestRepository({record.id: record})
    sonarr = series_sonarr(seasons={2: (8, True)}, monitor_new_seasons=True)

    await build_use_case(repository=repository, sonarr=sonarr).execute("req-1")

    assert sonarr.deleted == []


@pytest.mark.asyncio
async def test_removing_a_movie_request_unmonitors_it_in_radarr() -> None:
    record = make_record("req-2", media_type=MediaType.MOVIE, radarr_movie_id=31)
    repository = FakeMediaRequestRepository({record.id: record})
    radarr = movie_radarr(has_file=True)

    await build_use_case(repository=repository, radarr=radarr).execute("req-2")

    assert radarr.monitored == [(31, False)]
    assert radarr.deleted == []
    assert repository.records == {}


@pytest.mark.asyncio
async def test_a_movie_with_no_file_of_its_own_goes_with_its_last_request() -> None:
    record = make_record("req-2", media_type=MediaType.MOVIE, radarr_movie_id=31)
    repository = FakeMediaRequestRepository({record.id: record})
    radarr = movie_radarr()

    await build_use_case(repository=repository, radarr=radarr).execute("req-2")

    assert radarr.monitored == [(31, False)]
    assert radarr.deleted == [31]


@pytest.mark.asyncio
async def test_a_request_that_never_reached_an_arr_app_is_simply_dropped() -> None:
    record = make_record("req-3", season_number=1)
    repository = FakeMediaRequestRepository({record.id: record})
    sonarr = FakeSonarrService()
    radarr = FakeRadarrService()

    await build_use_case(repository=repository, sonarr=sonarr, radarr=radarr).execute("req-3")

    assert sonarr.monitored == []
    assert radarr.monitored == []
    assert repository.records == {}


@pytest.mark.asyncio
async def test_an_unknown_request_is_reported_rather_than_unmonitored() -> None:
    sonarr = FakeSonarrService()

    with pytest.raises(MediaRequestNotFoundError):
        await build_use_case(
            repository=FakeMediaRequestRepository(),
            sonarr=sonarr,
        ).execute("missing")

    assert sonarr.monitored == []
