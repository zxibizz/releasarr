"""Synchronise media requests with missing Radarr movies."""

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
from src.application.interfaces.radarr import MovieDetails, RadarrService
from src.application.interfaces.tmdb import TmdbMovieMetadata, TmdbService
from src.application.utility.localization import (
    LocalizationPicker,
    merge_default_localization,
)
from src.application.utility.sentinels import UNSET, _Unset
from src.core.logging import get_logger
from src.domain.enums import MediaRequestStatus, MediaType


@dataclass(slots=True)
class SyncRadarrResult:
    """Summary of the performed synchronisation."""

    created: int = 0
    updated: int = 0
    completed: int = 0


class SyncRadarrMediaRequestsUseCase:
    """Create or update media requests based on Radarr missing movies."""

    def __init__(
        self,
        *,
        repository: MediaRequestRepository,
        radarr_service: RadarrService,
        tmdb_service: TmdbService | None,
        metadata_languages: Sequence[str] | None = None,
        logger: Logger | None = None,
    ) -> None:
        self._repository = repository
        self._radarr = radarr_service
        self._tmdb = tmdb_service
        self._localization = LocalizationPicker(metadata_languages)
        self._metadata_languages = self._localization.languages
        self._logger = logger or get_logger(component="sync_radarr_requests")
        self._metadata_cache: dict[int, TmdbMovieMetadata | None] = {}

    async def execute(self) -> SyncRadarrResult:
        """Populate media requests for missing Radarr movies."""

        result = SyncRadarrResult()
        self._metadata_cache.clear()
        missing_movies = await self._radarr.get_missing_movies()
        missing_ids = {movie.id for movie in missing_movies}

        existing = await self._repository.list_radarr_requests()
        result.completed += await self._mark_completed(existing, missing_ids)

        for movie in missing_movies:
            outcome = await self._sync_movie(movie)
            if outcome == "created":
                result.created += 1
            elif outcome == "updated":
                result.updated += 1

        self._logger.info(
            "Radarr sync finished",
            created=result.created,
            updated=result.updated,
            completed=result.completed,
        )
        return result

    async def _sync_movie(self, details: MovieDetails) -> str:
        """Create or update a Radarr-backed request for a single movie."""

        existing = await self._repository.find_by_radarr(radarr_movie_id=details.id)

        metadata = await self._load_tmdb_metadata(details)
        localizations = self._build_localizations(metadata, details)

        title = self._localization.select(localizations, "title", details.title)
        overview = self._localization.select(localizations, "overview", details.overview) or None
        year = details.year or 0
        genres = list(details.genres)

        if existing is None:
            data = CreateMediaRequestData(
                id=uuid4().hex,
                media_type=MediaType.MOVIE,
                title=title,
                year=year,
                overview=overview,
                poster_url=details.poster_url,
                genres=genres,
                runtime_minutes=details.runtime_minutes,
                imdb_id=details.imdb_id,
                # The check constraint on media_requests keeps movies clear of the
                # series columns.
                season_number=None,
                total_episodes=None,
                series_title=None,
                series_year=None,
                status=MediaRequestStatus.PENDING,
                radarr_movie_id=details.id,
                localizations=localizations,
            )
            await self._repository.create_request(data)
            self._logger.debug(
                "Created media request for Radarr movie",
                radarr_movie_id=details.id,
                request_title=title,
            )
            return "created"

        # This is a metadata refresh for a movie Radarr still reports as missing.
        # Only a previously completed request needs to fall back to pending; an
        # in-flight status is owned by the release sync and must survive the refresh.
        status: MediaRequestStatus | _Unset = UNSET
        if existing.status == MediaRequestStatus.COMPLETED:
            status = MediaRequestStatus.PENDING

        update = UpdateMediaRequestData(
            title=title,
            year=year,
            overview=overview,
            poster_url=details.poster_url,
            genres=genres,
            status=status,
            runtime_minutes=details.runtime_minutes,
            imdb_id=details.imdb_id,
            radarr_movie_id=details.id,
            localizations=localizations,
        )
        await self._repository.update_request(existing.id, update)
        self._logger.debug(
            "Updated media request for Radarr movie",
            request_id=existing.id,
            radarr_movie_id=details.id,
        )
        return "updated"

    async def _mark_completed(
        self,
        existing: list[MediaRequestRecord],
        missing_ids: set[int],
    ) -> int:
        """Mark Radarr-linked requests as completed when no longer missing."""

        transitioned = 0
        for record in existing:
            if record.radarr_movie_id is None:
                continue
            if record.radarr_movie_id in missing_ids:
                continue
            if record.status == MediaRequestStatus.COMPLETED:
                continue
            update = UpdateMediaRequestData(status=MediaRequestStatus.COMPLETED)
            await self._repository.update_request(record.id, update)
            transitioned += 1
            self._logger.debug(
                "Marked Radarr movie as completed",
                request_id=record.id,
                radarr_movie_id=record.radarr_movie_id,
            )
        return transitioned

    async def _load_tmdb_metadata(self, details: MovieDetails) -> TmdbMovieMetadata | None:
        if self._tmdb is None or not details.tmdb_id:
            return None
        if details.tmdb_id in self._metadata_cache:
            return self._metadata_cache[details.tmdb_id]
        try:
            metadata = await self._tmdb.get_movie(details.tmdb_id, self._metadata_languages)
        except Exception as exc:  # pragma: no cover - defensive against HTTP failures
            self._logger.warning(
                "Failed to fetch TMDB metadata",
                error=str(exc),
                radarr_movie_id=details.id,
                tmdb_id=details.tmdb_id,
            )
            self._metadata_cache[details.tmdb_id] = None
            return None
        self._metadata_cache[details.tmdb_id] = metadata
        return metadata

    def _build_localizations(
        self,
        metadata: TmdbMovieMetadata | None,
        details: MovieDetails,
    ) -> dict[str, MediaLocalization]:
        localizations: dict[str, MediaLocalization] = {}
        if metadata is not None:
            for language, translation in metadata.translations.items():
                localizations[language] = MediaLocalization(
                    title=translation.title,
                    overview=translation.overview,
                )
        merge_default_localization(
            localizations,
            title=details.title,
            overview=details.overview,
        )
        return localizations


__all__ = ["SyncRadarrMediaRequestsUseCase", "SyncRadarrResult"]
