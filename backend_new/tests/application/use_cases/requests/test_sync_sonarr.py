"""Tests for syncing Sonarr missing seasons into media requests."""

from __future__ import annotations

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
from src.application.interfaces.sonarr import MissingSeriesRecord, SeriesDetails, SeriesSeasonDetails
from src.application.interfaces.tvdb import TvdbSeriesMetadata, TvdbTranslation, TvdbService
from src.application.use_cases.requests.sync_sonarr import SyncSonarrMediaRequestsUseCase
from src.domain.enums import MediaRequestStatus, MediaType


class FakeMediaRequestRepository(MediaRequestRepository):  # type: ignore[misc]
    def __init__(self, records: dict[str, MediaRequestRecord] | None = None) -> None:
        self.records = records or {}
        self.created: list[CreateMediaRequestData] = []
        self.updated: list[tuple[str, UpdateMediaRequestData]] = []

    async def list_requests(self, *args: Any, **kwargs: Any) -> tuple[list[MediaRequestRecord], int]:
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
            if value is None:
                continue
            setattr(record, field.name, value)
        record.updated_at = datetime.now(UTC)
        return record

    async def delete_request(self, request_id: str) -> bool:
        return self.records.pop(request_id, None) is not None

    async def find_by_sonarr(
        self,
        *,
        sonarr_series_id: int,
        season_number: int,
    ) -> MediaRequestRecord | None:
        for record in self.records.values():
            if (
                record.sonarr_series_id == sonarr_series_id
                and record.season_number == season_number
            ):
                return record
        return None

    async def list_sonarr_requests(self) -> list[MediaRequestRecord]:
        return [record for record in self.records.values() if record.sonarr_series_id is not None]


class FakeSonarrService:
    def __init__(
        self,
        missing: list[MissingSeriesRecord],
        catalogue: dict[int, SeriesDetails],
    ) -> None:
        self._missing = missing
        self._catalogue = catalogue
        self.series_calls: list[int] = []

    async def get_missing_series(self) -> list[MissingSeriesRecord]:
        return self._missing

    async def get_series(self, series_id: int) -> SeriesDetails:
        self.series_calls.append(series_id)
        return self._catalogue[series_id]


def make_series_details() -> SeriesDetails:
    return SeriesDetails(
        id=10,
        title="Example Show",
        year=2020,
        overview="A sample overview",
        poster_url="http://poster",
        imdb_id="tt1234567",
        tvdb_id=555,
        genres=["Drama"],
        seasons={
            1: SeriesSeasonDetails(
                season_number=1,
                episode_count=10,
                total_episode_count=10,
                episode_file_count=5,
            ),
            3: SeriesSeasonDetails(
                season_number=3,
                episode_count=8,
                total_episode_count=8,
                episode_file_count=0,
            ),
        },
    )


def make_existing_records() -> dict[str, MediaRequestRecord]:
    now = datetime.now(UTC)
    return {
        "req-1": MediaRequestRecord(
            id="req-1",
            media_type=MediaType.SERIES,
            status=MediaRequestStatus.COMPLETED,
            title="Old Title",
            year=2019,
            overview=None,
            poster_url=None,
            genres=["Mystery"],
            runtime_minutes=None,
            imdb_id="tt0000001",
            season_number=1,
            total_episodes=5,
            series_title="Legacy",
            series_year=2019,
            sonarr_series_id=10,
            created_at=now,
            updated_at=now,
            localizations={},
        ),
        "req-2": MediaRequestRecord(
            id="req-2",
            media_type=MediaType.SERIES,
            status=MediaRequestStatus.SEARCHING,
            title="Another Title",
            year=2018,
            overview=None,
            poster_url=None,
            genres=[],
            runtime_minutes=None,
            imdb_id=None,
            season_number=2,
            total_episodes=6,
            series_title="Legacy",
            series_year=2018,
            sonarr_series_id=10,
            created_at=now,
            updated_at=now,
            localizations={},
        ),
    }


class FakeTvdbService(TvdbService):
    def __init__(self, metadata: dict[int, TvdbSeriesMetadata]) -> None:
        self._metadata = metadata
        self.calls: list[tuple[int, tuple[str, ...]]] = []

    async def get_series(
        self,
        tvdb_id: int,
        languages: tuple[str, ...] | list[str] | None = None,
    ) -> TvdbSeriesMetadata:
        langs: tuple[str, ...]
        if languages is None:
            langs = ()
        elif isinstance(languages, tuple):
            langs = languages
        else:
            langs = tuple(languages)
        self.calls.append((tvdb_id, langs))
        return self._metadata[tvdb_id]


@pytest.mark.asyncio
async def test_sync_sonarr_creates_updates_and_completes() -> None:
    repository = FakeMediaRequestRepository(records=make_existing_records())
    missing = [MissingSeriesRecord(series_id=10, title="Example Show", season_numbers=[1, 3], tvdb_id=555, imdb_id="tt1234567")]
    sonarr = FakeSonarrService(missing=missing, catalogue={10: make_series_details()})
    tvdb_metadata = TvdbSeriesMetadata(
        tvdb_id=555,
        name="Example Show",
        overview="Default TVDB overview",
        image_url="http://tvdb/poster",
        year=2020,
        genres=["Drama"],
        translations={
            "eng": TvdbTranslation(language="eng", title="Example Show", overview="English overview"),
            "rus": TvdbTranslation(language="rus", title="Пример шоу", overview="Русское описание"),
        },
    )
    tvdb = FakeTvdbService(metadata={555: tvdb_metadata})

    use_case = SyncSonarrMediaRequestsUseCase(
        repository=repository,
        sonarr_service=sonarr,
        tvdb_service=tvdb,
        metadata_languages=("rus", "eng"),
    )
    result = await use_case.execute()

    assert result.created == 1
    assert result.updated == 1
    assert result.completed == 1

    # Season 1 should be updated to pending with refreshed metadata
    season_one = await repository.find_by_sonarr(sonarr_series_id=10, season_number=1)
    assert season_one is not None
    assert season_one.status == MediaRequestStatus.PENDING
    assert season_one.title == "Пример шоу - Season 1"
    assert season_one.total_episodes == 10
    assert season_one.imdb_id == "tt1234567"
    assert season_one.poster_url == "http://poster"
    assert "rus" in season_one.localizations
    assert season_one.localizations["rus"].title == "Пример шоу"
    assert season_one.localizations["eng"].title == "Example Show"

    # Season 2 should now be marked as completed
    season_two = await repository.find_by_sonarr(sonarr_series_id=10, season_number=2)
    assert season_two is not None
    assert season_two.status == MediaRequestStatus.COMPLETED

    # Season 3 should exist as a new request
    season_three = await repository.find_by_sonarr(sonarr_series_id=10, season_number=3)
    assert season_three is not None
    assert season_three.status == MediaRequestStatus.PENDING
    assert season_three.title == "Пример шоу - Season 3"
    assert season_three.series_title == "Example Show"
    assert season_three.series_year == 2020
    assert season_three.poster_url == "http://poster"
    assert season_three.localizations["eng"].overview == "English overview"
    assert season_three.localizations["rus"].overview == "Русское описание"

    # TVDB client should be invoked once per series
    assert tvdb.calls == [(555, ("rus", "eng"))]
