"""Synchronise media requests with the movies Radarr monitors."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import cast
from uuid import uuid4

from loguru._logger import Logger

from src.application.interfaces.media_requests import (
    CreateMediaRequestData,
    MediaLocalization,
    MediaRequestRepository,
    UpdateMediaRequestData,
)
from src.application.interfaces.radarr import MovieDetails, RadarrService
from src.application.interfaces.tmdb import TmdbMovieMetadata, TmdbService
from src.application.use_cases.requests.recompute_state import RecomputeRequestStateUseCase
from src.application.use_cases.requests.state import ArrCompletion
from src.application.utility.localization import (
    LocalizationPicker,
    merge_default_localization,
)
from src.application.utility.metadata_cache import SupportsWarning, get_cached_metadata
from src.application.utility.sentinels import UNSET, _Unset
from src.core.logging import get_logger
from src.domain.enums import LogComponent, MediaRequestStatus, MediaType


@dataclass(slots=True)
class SyncRadarrResult:
    """Summary of the performed synchronisation."""

    created: int = 0
    updated: int = 0
    deleted: int = 0


class SyncRadarrMediaRequestsUseCase:
    """Reconcile media requests with the movies Radarr monitors."""

    def __init__(
        self,
        *,
        repository: MediaRequestRepository,
        radarr_service: RadarrService,
        tmdb_service: TmdbService,
        recompute_state: RecomputeRequestStateUseCase,
        metadata_languages: Sequence[str] | None = None,
        logger: Logger | None = None,
    ) -> None:
        self._repository = repository
        self._radarr = radarr_service
        self._tmdb = tmdb_service
        self._recompute_state = recompute_state
        self._localization = LocalizationPicker(metadata_languages)
        self._metadata_languages = self._localization.languages
        self._logger = logger or get_logger(LogComponent.USECASE_SYNC_RADARR)
        self._metadata_cache: dict[int, TmdbMovieMetadata | None] = {}

    async def execute(self) -> SyncRadarrResult:
        """Reconcile media requests with the movies Radarr monitors."""

        result = SyncRadarrResult()
        self._metadata_cache.clear()
        library = await self._radarr.list_movies()
        wanted = {movie.id: movie for movie in library if movie.monitored}

        existing = await self._repository.list_radarr_requests()
        existing_ids = {
            record.radarr_movie_id: record
            for record in existing
            if record.radarr_movie_id is not None
        }

        # As on the Sonarr side, Radarr is the authority: a request whose movie
        # it no longer monitors - or no longer holds - has nothing left to be. An
        # empty library skips the pass so a restarting Radarr wipes nothing.
        if not library and existing:
            self._logger.warning(
                "Radarr reported an empty library; skipping request pruning",
                existing_requests=len(existing),
            )
        else:
            for movie_id, record in existing_ids.items():
                if movie_id in wanted:
                    continue
                await self._repository.delete_request(record.id)
                result.deleted += 1
                self._logger.info(
                    "Deleted request for a movie Radarr no longer monitors",
                    request_id=record.id,
                    radarr_movie_id=record.radarr_movie_id,
                    request_title=record.title,
                )

        # Every surviving request gets exactly one verdict, derived from Radarr's
        # own file state; the recompute is the only writer of status.
        verdicts: dict[str, ArrCompletion] = {}

        for movie in wanted.values():
            outcome = await self._sync_movie(movie, verdicts=verdicts)
            if outcome == "created":
                result.created += 1
            elif outcome == "updated":
                result.updated += 1

        if verdicts:
            await self._recompute_state.execute(sorted(verdicts), arr_completion=verdicts)

        self._logger.info(
            "Radarr sync finished",
            created=result.created,
            updated=result.updated,
            deleted=result.deleted,
        )
        return result

    async def sync_movie_by_id(
        self, movie_id: int, *, owner_user_id: str | None = None
    ) -> str | None:
        """Create or refresh the request for a single movie.

        Serves the add-request flow, where the request has to exist by the time
        the call returns. Completing and pruning belong to the full sweep alone.
        """

        self._metadata_cache.clear()
        details = await self._radarr.get_movie(movie_id)
        await self._sync_movie(details, owner_user_id=owner_user_id, reopen_completed=True)

        record = await self._repository.find_by_radarr(radarr_movie_id=movie_id)
        return None if record is None else record.id

    async def _sync_movie(
        self,
        details: MovieDetails,
        *,
        owner_user_id: str | None = None,
        verdicts: dict[str, ArrCompletion] | None = None,
        reopen_completed: bool = False,
    ) -> str:
        """Create or update a Radarr-backed request for a single movie."""

        existing = await self._repository.find_by_radarr(radarr_movie_id=details.id)

        # TMDB is the expensive leg of the sweep, and only the translations a row
        # is missing justify it; everything else comes from Radarr itself.
        if existing is not None and existing.localizations:
            localizations = existing.localizations
        else:
            metadata = await self._load_tmdb_metadata(details)
            localizations = self._build_localizations(metadata, details)

        verdict = ArrCompletion(is_complete=details.has_file)

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
                owner_user_id=owner_user_id,
            )
            await self._repository.create_request(data)
            self._logger.debug(
                "Created media request for Radarr movie",
                radarr_movie_id=details.id,
                request_title=title,
            )
            if verdicts is not None:
                verdicts[data.id] = verdict
            return "created"

        # What the verdict implies for the status is the recompute's call, not
        # this refresh's.
        if verdicts is not None:
            verdicts[existing.id] = verdict

        # As on the Sonarr side, an explicit re-request of a completed movie is
        # user intent and is written directly.
        status: MediaRequestStatus | _Unset = UNSET
        if reopen_completed and existing.status is MediaRequestStatus.COMPLETED:
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

    async def _load_tmdb_metadata(self, details: MovieDetails) -> TmdbMovieMetadata | None:
        if not self._tmdb.is_configured or details.tmdb_id is None:
            return None
        tmdb = self._tmdb
        tmdb_id = details.tmdb_id
        return await get_cached_metadata(
            cache=self._metadata_cache,
            lookup_id=tmdb_id,
            fetch=lambda: tmdb.get_movie(tmdb_id, self._metadata_languages),
            logger=cast(SupportsWarning, self._logger),
            provider_name="radarr_movie_id",
            entity_id=details.id,
            lookup_field="tmdb_id",
            warning_message="Failed to fetch TMDB metadata",
        )

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
