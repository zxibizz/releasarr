"""Tests for the season picker's option list."""

from __future__ import annotations

import pytest

from src.application.interfaces.sonarr import SeriesLookup
from src.application.interfaces.tvdb import TvdbSeriesMetadata
from src.application.use_cases.discover.exceptions import MediaNotFoundError
from src.application.use_cases.discover.list_season_options import ListSeasonOptionsUseCase
from tests.application.use_cases.discover.conftest import (
    FakeMediaRequestRepository,
    FakeSonarrService,
    FakeTvdbService,
    make_record,
    make_series_details,
)


def build_use_case(
    *,
    repository: FakeMediaRequestRepository | None = None,
    sonarr: FakeSonarrService | None = None,
    tvdb: FakeTvdbService | None = None,
) -> ListSeasonOptionsUseCase:
    return ListSeasonOptionsUseCase(
        repository=repository or FakeMediaRequestRepository(),
        sonarr_service=sonarr or FakeSonarrService(),
        tvdb_service=tvdb,
        metadata_languages=("eng",),
    )


@pytest.mark.asyncio
async def test_a_series_outside_the_library_offers_the_lookup_seasons() -> None:
    sonarr = FakeSonarrService(
        lookups={555: SeriesLookup(tvdb_id=555, title="Example Show", season_numbers=[1, 2, 3])}
    )

    result = await build_use_case(sonarr=sonarr).execute(555)

    assert result.in_library is False
    assert result.library_id is None
    assert [season.season_number for season in result.seasons] == [1, 2, 3]
    assert all(season.requested is False for season in result.seasons)


@pytest.mark.asyncio
async def test_an_added_series_reports_monitoring_and_existing_requests() -> None:
    repository = FakeMediaRequestRepository(
        records={"req-1": make_record("req-1", season_number=1, sonarr_series_id=12)}
    )
    sonarr = FakeSonarrService(
        lookups={
            555: SeriesLookup(
                tvdb_id=555,
                title="Example Show",
                existing_series_id=12,
                season_numbers=[1, 2],
            )
        },
        catalogue={12: make_series_details(12, seasons={1: (10, True), 2: (8, False)})},
    )

    result = await build_use_case(repository=repository, sonarr=sonarr).execute(555)

    assert result.in_library is True
    assert result.library_id == 12
    first, second = result.seasons
    assert (first.season_number, first.monitored, first.requested) == (1, True, True)
    assert first.request_id == "req-1"
    assert (second.season_number, second.monitored, second.requested) == (2, False, False)
    assert second.request_id is None


@pytest.mark.asyncio
async def test_seasons_known_only_to_the_lookup_are_still_offered() -> None:
    """A season Sonarr has not yet pulled in must remain requestable."""

    sonarr = FakeSonarrService(
        lookups={
            555: SeriesLookup(
                tvdb_id=555,
                title="Example Show",
                existing_series_id=12,
                season_numbers=[1, 2, 3],
            )
        },
        catalogue={12: make_series_details(12, seasons={1: (10, True)})},
    )

    result = await build_use_case(sonarr=sonarr).execute(555)

    assert [season.season_number for season in result.seasons] == [1, 2, 3]
    assert result.seasons[2].monitored is False


@pytest.mark.asyncio
async def test_tvdb_seasons_cover_a_series_sonarr_cannot_resolve_yet() -> None:
    tvdb = FakeTvdbService(
        metadata={
            555: TvdbSeriesMetadata(
                tvdb_id=555,
                name="Brand New Show",
                overview="An overview",
                image_url=None,
                year=2026,
                genres=[],
                translations={},
                seasons=[0, 1],
            ),
        }
    )

    result = await build_use_case(sonarr=FakeSonarrService(), tvdb=tvdb).execute(555)

    assert result.in_library is False
    assert [season.season_number for season in result.seasons] == [0, 1]


@pytest.mark.asyncio
async def test_an_unresolvable_series_without_tvdb_is_reported_as_missing() -> None:
    with pytest.raises(MediaNotFoundError):
        await build_use_case().execute(555)
