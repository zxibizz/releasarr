"""Synchronise media requests with missing Sonarr seasons."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from uuid import uuid4

from loguru._logger import Logger

from src.application.interfaces.media_requests import (
    CreateMediaRequestData,
    MediaLocalization,
    MediaRequestRecord,
    MediaRequestRepository,
    UpdateMediaRequestData,
)
from src.application.interfaces.sonarr import SeriesDetails, SonarrService
from src.application.interfaces.tvdb import TvdbSeriesMetadata, TvdbService
from src.application.utility.localization import (
    LocalizationPicker,
    merge_default_localization,
)
from src.application.utility.sentinels import UNSET, _Unset
from src.core.logging import get_logger
from src.domain.enums import MediaRequestStatus, MediaType


@dataclass(slots=True)
class SyncSonarrResult:
    """Summary of the performed synchronisation."""

    created: int = 0
    updated: int = 0
    completed: int = 0


class SyncSonarrMediaRequestsUseCase:
    """Create or update media requests based on Sonarr missing seasons."""

    def __init__(
        self,
        *,
        repository: MediaRequestRepository,
        sonarr_service: SonarrService,
        tvdb_service: TvdbService | None,
        metadata_languages: Sequence[str] | None = None,
        logger: Logger | None = None,
    ) -> None:
        self._repository = repository
        self._sonarr = sonarr_service
        self._tvdb = tvdb_service
        self._localization = LocalizationPicker(metadata_languages)
        self._metadata_languages = self._localization.languages
        self._logger = logger or get_logger(component="sync_sonarr_requests")
        self._metadata_cache: dict[int, TvdbSeriesMetadata | None] = {}

    async def execute(self) -> SyncSonarrResult:
        """Populate media requests for missing Sonarr seasons."""

        result = SyncSonarrResult()
        self._metadata_cache.clear()
        missing_series = await self._sonarr.get_missing_series()
        missing_keys = {
            (item.series_id, season_number)
            for item in missing_series
            for season_number in item.season_numbers
        }

        existing = await self._repository.list_sonarr_requests()
        result.completed += await self._mark_completed(existing, missing_keys)

        for series in missing_series:
            details = await self._sonarr.get_series(series.series_id)
            for season_number in series.season_numbers:
                updated = await self._sync_season(details, season_number)
                if updated == "created":
                    result.created += 1
                elif updated == "updated":
                    result.updated += 1

        self._logger.info(
            "Sonarr sync finished",
            created=result.created,
            updated=result.updated,
            completed=result.completed,
        )
        return result

    async def _sync_season(self, details: SeriesDetails, season_number: int) -> str:
        """Create or update a Sonarr-backed request for a specific season."""

        existing = await self._repository.find_by_sonarr(
            sonarr_series_id=details.id,
            season_number=season_number,
        )

        metadata = await self._load_tvdb_metadata(details)
        localizations = self._build_localizations(metadata, details, season_number)

        season_info = details.seasons.get(season_number)
        total_episodes = season_info.total_episode_count if season_info else 0
        localized_series_title = self._localization.select(localizations, "title", details.title)
        title = self._build_request_title(localized_series_title, season_number)
        year = details.year or 0
        series_year = details.year or year
        genres = list(details.genres)
        imdb_id = details.imdb_id
        overview_value = self._localization.select(localizations, "overview", details.overview)
        overview = overview_value or None
        poster_url = details.poster_url or (metadata.image_url if metadata else None)

        if existing is None:
            data = CreateMediaRequestData(
                id=uuid4().hex,
                media_type=MediaType.SERIES,
                title=title,
                year=year,
                overview=overview,
                poster_url=poster_url,
                genres=genres,
                runtime_minutes=None,
                imdb_id=imdb_id,
                season_number=season_number,
                total_episodes=total_episodes,
                series_title=details.title,
                series_year=series_year,
                status=MediaRequestStatus.PENDING,
                sonarr_series_id=details.id,
                localizations=localizations,
            )
            await self._repository.create_request(data)
            self._logger.debug(
                "Created media request for Sonarr season",
                sonarr_series_id=details.id,
                season_number=season_number,
                request_title=title,
            )
            return "created"

        # This is a metadata refresh for a season Sonarr still reports as missing.
        # Only a previously completed request needs to fall back to pending; an
        # in-flight status is owned by the release sync and must survive the refresh.
        status: MediaRequestStatus | _Unset = UNSET
        if existing.status == MediaRequestStatus.COMPLETED:
            status = MediaRequestStatus.PENDING

        update = UpdateMediaRequestData(
            title=title,
            year=year,
            overview=overview,
            poster_url=poster_url,
            genres=genres,
            status=status,
            imdb_id=imdb_id,
            season_number=season_number,
            total_episodes=total_episodes,
            series_title=details.title,
            series_year=series_year,
            sonarr_series_id=details.id,
            localizations=localizations,
        )
        await self._repository.update_request(existing.id, update)
        self._logger.debug(
            "Updated media request for Sonarr season",
            request_id=existing.id,
            sonarr_series_id=details.id,
            season_number=season_number,
        )
        return "updated"

    async def _mark_completed(
        self,
        existing: list[MediaRequestRecord],
        missing_keys: set[tuple[int, int]],
    ) -> int:
        """Mark Sonarr-linked requests as completed when no longer missing."""

        transitioned = 0
        for record in existing:
            if record.sonarr_series_id is None or record.season_number is None:
                continue
            key = (record.sonarr_series_id, record.season_number)
            if key in missing_keys:
                continue
            if record.status == MediaRequestStatus.COMPLETED:
                continue
            update = UpdateMediaRequestData(status=MediaRequestStatus.COMPLETED)
            await self._repository.update_request(record.id, update)
            transitioned += 1
            self._logger.debug(
                "Marked Sonarr season as completed",
                request_id=record.id,
                sonarr_series_id=record.sonarr_series_id,
                season_number=record.season_number,
            )
        return transitioned

    def _build_request_title(self, series_title: str, season_number: int) -> str:
        if season_number <= 0:
            return f"{series_title} - Specials"
        return f"{series_title} - Season {season_number}"

    async def _load_tvdb_metadata(self, details: SeriesDetails) -> TvdbSeriesMetadata | None:
        if self._tvdb is None or not details.tvdb_id:
            return None
        cached = self._metadata_cache.get(details.tvdb_id)
        if cached is not None or details.tvdb_id in self._metadata_cache:
            return cached
        try:
            metadata = await self._tvdb.get_series(details.tvdb_id, self._metadata_languages)
        except Exception as exc:  # pragma: no cover - defensive against HTTP failures
            self._logger.warning(
                "Failed to fetch TVDB metadata",
                error=str(exc),
                sonarr_series_id=details.id,
                tvdb_id=details.tvdb_id,
            )
            self._metadata_cache[details.tvdb_id] = None
            return None
        self._metadata_cache[details.tvdb_id] = metadata
        return metadata

    def _build_localizations(
        self,
        metadata: TvdbSeriesMetadata | None,
        details: SeriesDetails,
        season_number: int,
    ) -> dict[str, MediaLocalization]:
        localizations: dict[str, MediaLocalization] = {}
        if metadata is not None:
            for language, translation in metadata.translations.items():
                season_overview = translation.season_overviews.get(season_number)
                localizations[language] = MediaLocalization(
                    title=translation.title,
                    overview=season_overview or translation.overview,
                )
        merge_default_localization(
            localizations,
            title=details.title,
            overview=details.overview,
        )
        return localizations


__all__ = ["SyncSonarrMediaRequestsUseCase", "SyncSonarrResult"]
