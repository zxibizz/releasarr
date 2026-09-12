"""Tests for syncing Radarr missing movies into media requests."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import fields
from datetime import UTC, datetime
from typing import Any

import pytest

from src.application.interfaces.media_requests import (
    CreateMediaRequestData,
    MediaRequestRecord,
    MediaRequestRepository,
    UpdateMediaRequestData,
)
from src.application.interfaces.radarr import MovieDetails, MovieImportFile
from src.application.interfaces.tmdb import TmdbMovieMetadata, TmdbService, TmdbTranslation
from src.application.use_cases.requests.sync_radarr import SyncRadarrMediaRequestsUseCase
from src.application.utility.sentinels import UNSET
from src.domain.enums import MediaRequestStatus, MediaType


class FakeMediaRequestRepository(MediaRequestRepository):
    def __init__(self, records: dict[str, MediaRequestRecord] | None = None) -> None:
        self.records = records or {}
        self.created: list[CreateMediaRequestData] = []
        self.updated: list[tuple[str, UpdateMediaRequestData]] = []

    async def list_requests(
        self, *args: Any, **kwargs: Any
    ) -> tuple[list[MediaRequestRecord], int]:
        raise NotImplementedError

    async def create_request(self, data: CreateMediaRequestData) -> MediaRequestRecord:
        self.created.append(data)
        record = MediaRequestRecord(
            id=data.id,
            media_type=data.media_type,
            status=data.status,
            title=data.title,
            year=data.year,
            overview=data.overview,
            poster_url=data.poster_url,
            genres=list(data.genres),
            runtime_minutes=data.runtime_minutes,
            imdb_id=data.imdb_id,
            season_number=data.season_number,
            total_episodes=data.total_episodes,
            series_title=data.series_title,
            series_year=data.series_year,
            sonarr_series_id=data.sonarr_series_id,
            radarr_movie_id=data.radarr_movie_id,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            localizations=data.localizations,
        )
        self.records[record.id] = record
        return record

    async def get_request(self, request_id: str) -> MediaRequestRecord | None:
        return self.records.get(request_id)

    async def update_request(
        self,
        request_id: str,
        data: UpdateMediaRequestData,
    ) -> MediaRequestRecord | None:
        record = self.records.get(request_id)
        if record is None:
            return None
        self.updated.append((request_id, data))
        for field in fields(UpdateMediaRequestData):
            value = getattr(data, field.name)
            if value is UNSET:
                continue
            setattr(record, field.name, value)
        record.updated_at = datetime.now(UTC)
        return record

    async def delete_request(self, request_id: str) -> bool:
        return self.records.pop(request_id, None) is not None

    async def find_by_radarr(self, *, radarr_movie_id: int) -> MediaRequestRecord | None:
        for record in self.records.values():
            if record.radarr_movie_id == radarr_movie_id:
                return record
        return None

    async def list_radarr_requests(self) -> list[MediaRequestRecord]:
        return [record for record in self.records.values() if record.radarr_movie_id is not None]


class FakeRadarrService:
    def __init__(self, missing: list[MovieDetails]) -> None:
        self._missing = missing

    async def get_missing_movies(self) -> list[MovieDetails]:
        return self._missing

    async def get_movie(self, movie_id: int) -> MovieDetails:
        return next(movie for movie in self._missing if movie.id == movie_id)

    async def manual_import(self, files: list[MovieImportFile]) -> bool:
        return True


class FakeTmdbService(TmdbService):
    def __init__(self, metadata: dict[int, TmdbMovieMetadata]) -> None:
        self._metadata = metadata
        self.calls: list[tuple[int, tuple[str, ...]]] = []

    async def get_movie(
        self,
        tmdb_id: int,
        languages: Sequence[str] | None = None,
    ) -> TmdbMovieMetadata:
        self.calls.append((tmdb_id, () if languages is None else tuple(languages)))
        return self._metadata[tmdb_id]


def make_movie(movie_id: int = 156, title: str = "Arrival") -> MovieDetails:
    return MovieDetails(
        id=movie_id,
        title=title,
        year=2016,
        overview="Linguist meets heptapods.",
        poster_url="http://poster",
        imdb_id="tt2543164",
        tmdb_id=329865,
        genres=["Drama"],
        runtime_minutes=116,
        has_file=False,
    )


def make_record(
    request_id: str,
    radarr_movie_id: int,
    status: MediaRequestStatus,
) -> MediaRequestRecord:
    now = datetime.now(UTC)
    return MediaRequestRecord(
        id=request_id,
        media_type=MediaType.MOVIE,
        status=status,
        title="Old Title",
        year=2015,
        overview=None,
        poster_url=None,
        genres=[],
        runtime_minutes=None,
        imdb_id=None,
        season_number=None,
        total_episodes=None,
        series_title=None,
        series_year=None,
        radarr_movie_id=radarr_movie_id,
        created_at=now,
        updated_at=now,
        localizations={},
    )


@pytest.mark.asyncio
async def test_sync_radarr_creates_updates_and_completes() -> None:
    repository = FakeMediaRequestRepository(
        records={
            # Still missing, so it is refreshed and reopened.
            "req-1": make_record("req-1", 156, MediaRequestStatus.COMPLETED),
            # No longer reported missing, so Radarr now has it.
            "req-2": make_record("req-2", 999, MediaRequestStatus.PENDING),
        }
    )
    radarr = FakeRadarrService([make_movie(), make_movie(200, "Dune")])
    tmdb = FakeTmdbService(
        metadata={
            329865: TmdbMovieMetadata(
                tmdb_id=329865,
                translations={
                    "eng": TmdbTranslation(
                        language="eng",
                        title="Arrival",
                        overview="English overview",
                    ),
                    "rus": TmdbTranslation(
                        language="rus",
                        title="Прибытие",
                        overview="Русское описание",
                    ),
                },
            )
        }
    )

    use_case = SyncRadarrMediaRequestsUseCase(
        repository=repository,
        radarr_service=radarr,
        tmdb_service=tmdb,
        metadata_languages=("rus", "eng"),
    )
    result = await use_case.execute()

    assert (result.created, result.updated, result.completed) == (1, 1, 1)

    refreshed = await repository.find_by_radarr(radarr_movie_id=156)
    assert refreshed is not None
    assert refreshed.status == MediaRequestStatus.PENDING
    assert refreshed.title == "Прибытие"
    assert refreshed.overview == "Русское описание"
    assert refreshed.runtime_minutes == 116
    assert refreshed.imdb_id == "tt2543164"
    assert refreshed.localizations["eng"].title == "Arrival"

    gone = await repository.find_by_radarr(radarr_movie_id=999)
    assert gone is not None
    assert gone.status == MediaRequestStatus.COMPLETED

    created = await repository.find_by_radarr(radarr_movie_id=200)
    assert created is not None
    assert created.media_type == MediaType.MOVIE
    # The check constraint on media_requests rejects a movie carrying season fields.
    assert created.season_number is None
    assert created.total_episodes is None

    # Only the movie TMDB knows about is looked up, once.
    assert tmdb.calls == [(329865, ("rus", "eng"))]


@pytest.mark.asyncio
async def test_sync_radarr_preserves_in_flight_status() -> None:
    """A metadata refresh must not knock a downloading movie back to pending."""

    repository = FakeMediaRequestRepository(
        records={"req-1": make_record("req-1", 156, MediaRequestStatus.DOWNLOADING)}
    )

    use_case = SyncRadarrMediaRequestsUseCase(
        repository=repository,
        radarr_service=FakeRadarrService([make_movie()]),
        tmdb_service=None,
    )
    await use_case.execute()

    record = await repository.find_by_radarr(radarr_movie_id=156)
    assert record is not None
    assert record.status == MediaRequestStatus.DOWNLOADING
    # The rest of the metadata is still refreshed.
    assert record.title == "Arrival"
    assert record.runtime_minutes == 116


@pytest.mark.asyncio
async def test_sync_radarr_falls_back_to_radarr_metadata_without_tmdb() -> None:
    """Radarr's own title still has to land under the default language."""

    repository = FakeMediaRequestRepository()

    use_case = SyncRadarrMediaRequestsUseCase(
        repository=repository,
        radarr_service=FakeRadarrService([make_movie()]),
        tmdb_service=None,
        metadata_languages=("rus", "eng"),
    )
    await use_case.execute()

    record = await repository.find_by_radarr(radarr_movie_id=156)
    assert record is not None
    assert record.title == "Arrival"
    assert record.localizations["eng"].title == "Arrival"
    assert record.localizations["eng"].overview == "Linguist meets heptapods."
