"""Tests for merging provider search results with library and request state."""

from __future__ import annotations

import pytest

from src.application.interfaces.radarr import MovieLookup
from src.application.interfaces.sonarr import SeriesLookup
from src.application.interfaces.tmdb import TmdbSearchResult
from src.application.interfaces.tvdb import TvdbSearchResult
from src.application.use_cases.discover.exceptions import MetadataProviderUnavailableError
from src.application.use_cases.discover.search_media import SearchMediaUseCase
from src.domain.enums import MediaRequestStatus, MediaType
from tests.application.use_cases.discover.conftest import (
    FakeMediaRequestRepository,
    FakeRadarrService,
    FakeSonarrService,
    FakeTmdbService,
    FakeTvdbService,
    make_record,
)

SERIES_MATCHES = [
    TvdbSearchResult(tvdb_id=555, name="Example Show", year=2020, overview="An overview"),
    TvdbSearchResult(tvdb_id=556, name="Other Show", year=2021),
]

MOVIE_MATCHES = [
    TmdbSearchResult(tmdb_id=777, title="Example Movie", year=2021),
    TmdbSearchResult(tmdb_id=778, title="Other Movie", year=2022),
]


def build_use_case(
    *,
    repository: FakeMediaRequestRepository | None = None,
    sonarr: FakeSonarrService | None = None,
    radarr: FakeRadarrService | None = None,
    tvdb: FakeTvdbService | None = None,
    tmdb: FakeTmdbService | None = None,
) -> SearchMediaUseCase:
    return SearchMediaUseCase(
        repository=repository or FakeMediaRequestRepository(),
        sonarr_service=sonarr or FakeSonarrService(),
        radarr_service=radarr or FakeRadarrService(),
        tvdb_service=tvdb if tvdb is not None else FakeTvdbService(search_results=SERIES_MATCHES),
        tmdb_service=tmdb if tmdb is not None else FakeTmdbService(search_results=MOVIE_MATCHES),
        metadata_languages=("rus", "eng"),
    )


@pytest.mark.asyncio
async def test_series_in_the_library_report_their_requested_seasons() -> None:
    repository = FakeMediaRequestRepository(
        records={
            "req-1": make_record("req-1", season_number=1, sonarr_series_id=12),
            "req-2": make_record("req-2", season_number=3, sonarr_series_id=12),
            # A different series' request must not leak into the result.
            "req-3": make_record("req-3", season_number=1, sonarr_series_id=99),
        }
    )
    sonarr = FakeSonarrService(
        search_results=[
            SeriesLookup(tvdb_id=555, title="Example Show", existing_series_id=12),
            SeriesLookup(tvdb_id=556, title="Other Show"),
        ]
    )

    results = await build_use_case(repository=repository, sonarr=sonarr).execute(
        "example", MediaType.SERIES
    )

    assert [result.provider_id for result in results] == [555, 556]
    assert results[0].in_library is True
    assert results[0].library_id == 12
    assert results[0].requested_seasons == [1, 3]
    # Sonarr reported the second series with id 0, so it is not in the library.
    assert results[1].in_library is False
    assert results[1].requested_seasons == []


@pytest.mark.asyncio
async def test_a_series_in_the_library_with_no_requests_reports_none() -> None:
    sonarr = FakeSonarrService(
        search_results=[SeriesLookup(tvdb_id=555, title="Example Show", existing_series_id=12)]
    )

    results = await build_use_case(sonarr=sonarr).execute("example", MediaType.SERIES)

    assert results[0].in_library is True
    assert results[0].requested_seasons == []


@pytest.mark.asyncio
async def test_results_absent_from_the_lookup_are_left_unannotated() -> None:
    """The provider owns the result list, so a hit Sonarr never saw still shows."""

    sonarr = FakeSonarrService(search_results=[])

    results = await build_use_case(sonarr=sonarr).execute("example", MediaType.SERIES)

    assert len(results) == 2
    assert all(result.in_library is False for result in results)


@pytest.mark.asyncio
async def test_an_unreachable_sonarr_does_not_fail_the_search() -> None:
    sonarr = FakeSonarrService(search_error=RuntimeError("connection refused"))

    results = await build_use_case(sonarr=sonarr).execute("example", MediaType.SERIES)

    assert [result.title for result in results] == ["Example Show", "Other Show"]
    assert all(result.in_library is False for result in results)


@pytest.mark.asyncio
async def test_movies_in_the_library_report_their_request() -> None:
    repository = FakeMediaRequestRepository(
        records={
            "req-1": make_record(
                "req-1",
                media_type=MediaType.MOVIE,
                radarr_movie_id=31,
                status=MediaRequestStatus.DOWNLOADING,
            )
        }
    )
    radarr = FakeRadarrService(
        search_results=[
            MovieLookup(tmdb_id=777, title="Example Movie", existing_movie_id=31),
            MovieLookup(tmdb_id=778, title="Other Movie"),
        ]
    )

    results = await build_use_case(repository=repository, radarr=radarr).execute(
        "example", MediaType.MOVIE
    )

    assert results[0].library_id == 31
    assert results[0].request_id == "req-1"
    assert results[0].request_status == MediaRequestStatus.DOWNLOADING
    assert results[1].in_library is False
    assert results[1].request_id is None


@pytest.mark.asyncio
async def test_an_unreachable_radarr_does_not_fail_the_search() -> None:
    radarr = FakeRadarrService(search_error=RuntimeError("connection refused"))

    results = await build_use_case(radarr=radarr).execute("example", MediaType.MOVIE)

    assert [result.title for result in results] == ["Example Movie", "Other Movie"]


@pytest.mark.asyncio
async def test_searching_without_a_metadata_provider_is_reported() -> None:
    use_case = SearchMediaUseCase(
        repository=FakeMediaRequestRepository(),
        sonarr_service=FakeSonarrService(),
        radarr_service=FakeRadarrService(),
        tvdb_service=None,
        tmdb_service=None,
        metadata_languages=("eng",),
    )

    with pytest.raises(MetadataProviderUnavailableError) as excinfo:
        await use_case.execute("example", MediaType.SERIES)

    assert "RELEASARR_TVDB_API_KEY" in str(excinfo.value)


@pytest.mark.asyncio
async def test_a_blank_query_searches_nothing() -> None:
    """Short-circuited before the provider, which would reject it anyway."""

    assert await build_use_case().execute("   ", MediaType.SERIES) == []


@pytest.mark.asyncio
async def test_searching_without_a_type_returns_both_kinds() -> None:
    results = await build_use_case().execute("example")

    assert {result.provider_id for result in results} == {555, 556, 777, 778}
    assert {result.media_type for result in results} == {MediaType.SERIES, MediaType.MOVIE}


@pytest.mark.asyncio
async def test_a_combined_search_puts_the_closest_titles_first() -> None:
    """Neither provider's ranking knows about the other, so titles decide."""

    tvdb = FakeTvdbService(
        search_results=[
            TvdbSearchResult(tvdb_id=1, name="Behind The Example"),
            TvdbSearchResult(tvdb_id=2, name="Example Show"),
        ]
    )
    tmdb = FakeTmdbService(
        search_results=[
            TmdbSearchResult(tmdb_id=3, title="Example"),
            TmdbSearchResult(tmdb_id=4, title="Unrelated"),
        ]
    )

    results = await build_use_case(tvdb=tvdb, tmdb=tmdb).execute("example")

    assert [result.title for result in results] == [
        "Example",
        "Example Show",
        "Behind The Example",
        "Unrelated",
    ]


@pytest.mark.asyncio
async def test_a_combined_search_uses_whichever_provider_is_configured() -> None:
    use_case = SearchMediaUseCase(
        repository=FakeMediaRequestRepository(),
        sonarr_service=FakeSonarrService(),
        radarr_service=FakeRadarrService(),
        tvdb_service=None,
        tmdb_service=FakeTmdbService(search_results=MOVIE_MATCHES),
        metadata_languages=("eng",),
    )

    results = await use_case.execute("example")

    assert [result.provider_id for result in results] == [777, 778]


@pytest.mark.asyncio
async def test_a_combined_search_with_no_provider_names_both() -> None:
    use_case = SearchMediaUseCase(
        repository=FakeMediaRequestRepository(),
        sonarr_service=FakeSonarrService(),
        radarr_service=FakeRadarrService(),
        tvdb_service=None,
        tmdb_service=None,
        metadata_languages=("eng",),
    )

    with pytest.raises(MetadataProviderUnavailableError) as excinfo:
        await use_case.execute("example")

    assert "RELEASARR_TVDB_API_KEY" in str(excinfo.value)
    assert "RELEASARR_TMDB_API_KEY" in str(excinfo.value)


@pytest.mark.asyncio
async def test_a_combined_search_survives_one_failing_provider() -> None:
    tvdb = FakeTvdbService(search_error=RuntimeError("connection refused"))

    results = await build_use_case(tvdb=tvdb).execute("example")

    assert [result.provider_id for result in results] == [777, 778]


@pytest.mark.asyncio
async def test_a_combined_search_fails_when_every_provider_fails() -> None:
    tvdb = FakeTvdbService(search_error=RuntimeError("tvdb is down"))
    tmdb = FakeTmdbService(search_error=RuntimeError("tmdb is down"))

    with pytest.raises(RuntimeError, match="tvdb is down"):
        await build_use_case(tvdb=tvdb, tmdb=tmdb).execute("example")


@pytest.mark.asyncio
async def test_the_requested_language_is_asked_for_first() -> None:
    tvdb = FakeTvdbService(search_results=SERIES_MATCHES)

    await build_use_case(tvdb=tvdb).execute("example", MediaType.SERIES, "ru")

    # Configured as ("rus", "eng"), so the request only reorders what is there.
    assert tvdb.search_languages == [["rus", "eng"]]


@pytest.mark.asyncio
async def test_a_requested_language_outside_the_configured_ones_still_wins() -> None:
    tmdb = FakeTmdbService(search_results=MOVIE_MATCHES)

    await build_use_case(tmdb=tmdb).execute("example", MediaType.MOVIE, "de")

    assert tmdb.search_languages == [["deu", "rus", "eng"]]


@pytest.mark.asyncio
async def test_an_unknown_language_falls_back_to_the_configured_ones() -> None:
    """Better to show results in another language than to show none at all."""

    tvdb = FakeTvdbService(search_results=SERIES_MATCHES)

    await build_use_case(tvdb=tvdb).execute("example", MediaType.SERIES, "klingon")

    assert tvdb.search_languages == [["rus", "eng"]]
