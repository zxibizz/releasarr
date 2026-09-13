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
    make_record,
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


@pytest.mark.asyncio
async def test_removing_a_season_request_unmonitors_it_in_sonarr() -> None:
    """Left monitored, the next sync would hand the request straight back."""

    record = make_record("req-1", season_number=2, sonarr_series_id=12)
    repository = FakeMediaRequestRepository({record.id: record})
    sonarr = FakeSonarrService()

    await build_use_case(repository=repository, sonarr=sonarr).execute("req-1")

    # The new-season flag is left unstated, removing one request being no
    # verdict on whether future seasons are still wanted.
    assert sonarr.monitored == [
        {"series_id": 12, "monitor": [], "unmonitor": [2], "monitor_new_seasons": None}
    ]
    assert repository.records == {}


@pytest.mark.asyncio
async def test_removing_a_movie_request_unmonitors_it_in_radarr() -> None:
    record = make_record("req-2", media_type=MediaType.MOVIE, radarr_movie_id=31)
    repository = FakeMediaRequestRepository({record.id: record})
    radarr = FakeRadarrService()

    await build_use_case(repository=repository, radarr=radarr).execute("req-2")

    assert radarr.monitored == [(31, False)]
    assert repository.records == {}


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
