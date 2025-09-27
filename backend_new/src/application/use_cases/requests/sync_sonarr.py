"""Synchronise media requests with missing Sonarr seasons."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from src.application.interfaces.media_requests import (
    CreateMediaRequestData,
    MediaRequestRecord,
    MediaRequestRepository,
    UpdateMediaRequestData,
)
from src.application.interfaces.sonarr import MissingSeriesRecord, SeriesDetails, SonarrService
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
        logger: Logger | None = None,
    ) -> None:
        self._repository = repository
        self._sonarr = sonarr_service
        self._logger = logger or get_logger(component="sync_sonarr_requests")

    async def execute(self) -> SyncSonarrResult:
        """Populate media requests for missing Sonarr seasons."""

        result = SyncSonarrResult()
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

        season_info = details.seasons.get(season_number)
        total_episodes = season_info.total_episode_count if season_info else 0
        title = self._build_request_title(details.title, season_number)
        year = details.year or 0
        series_year = details.year or year
        genres = list(details.genres)
        imdb_id = details.imdb_id
        overview = details.overview
        poster_url = details.poster_url

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
            )
            await self._repository.create_request(data)
            self._logger.debug(
                "Created media request for Sonarr season",
                sonarr_series_id=details.id,
                season_number=season_number,
                request_title=title,
            )
            return "created"

        update = UpdateMediaRequestData(
            title=title,
            year=year,
            overview=overview,
            poster_url=poster_url,
            genres=genres,
            status=MediaRequestStatus.PENDING,
            imdb_id=imdb_id,
            season_number=season_number,
            total_episodes=total_episodes,
            series_title=details.title,
            series_year=series_year,
            sonarr_series_id=details.id,
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


__all__ = ["SyncSonarrMediaRequestsUseCase", "SyncSonarrResult"]
