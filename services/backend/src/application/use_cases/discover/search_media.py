"""Search TVDB/TMDB and annotate the hits with what we already hold."""

from __future__ import annotations

import asyncio
from collections.abc import Coroutine, Sequence

from loguru._logger import Logger

from src.application.interfaces.media_requests import (
    MediaRequestRecord,
    MediaRequestRepository,
)
from src.application.interfaces.radarr import MovieLookup, RadarrService
from src.application.interfaces.sonarr import SeriesLookup, SonarrService
from src.application.interfaces.tmdb import TmdbSearchResult, TmdbService
from src.application.interfaces.tvdb import TvdbSearchResult, TvdbService
from src.application.use_cases.discover.dto import MediaSearchResultDTO
from src.application.use_cases.discover.exceptions import MetadataProviderUnavailableError
from src.application.use_cases.discover.request_state import (
    requested_movies,
    requested_seasons_by_series,
)
from src.application.utility.languages import to_three_letter
from src.core.logging import get_logger
from src.domain.enums import MediaType


class SearchMediaUseCase:
    """Find media to request, and say what is already in the library.

    The metadata provider owns the result list; Sonarr/Radarr and our own
    requests only annotate it. The library annotation is best-effort - a search
    that cannot reach Sonarr is still far more useful than no search at all - so
    a failure there is logged and the results go out unannotated.
    """

    def __init__(
        self,
        *,
        repository: MediaRequestRepository,
        sonarr_service: SonarrService,
        radarr_service: RadarrService,
        tvdb_service: TvdbService | None,
        tmdb_service: TmdbService | None,
        metadata_languages: Sequence[str] | None = None,
        logger: Logger | None = None,
    ) -> None:
        self._repository = repository
        self._sonarr = sonarr_service
        self._radarr = radarr_service
        self._tvdb = tvdb_service
        self._tmdb = tmdb_service
        self._metadata_languages = tuple(metadata_languages or ())
        self._logger = logger or get_logger(component="search_media")

    async def execute(
        self,
        query: str,
        media_type: MediaType | None = None,
        language: str | None = None,
    ) -> list[MediaSearchResultDTO]:
        """Search for media, over both types when the caller does not name one."""

        term = query.strip()
        if not term:
            return []

        languages = self._languages_for(language)
        if media_type == MediaType.SERIES:
            return await self._search_series(term, languages)
        if media_type == MediaType.MOVIE:
            return await self._search_movies(term, languages)
        return await self._search_both(term, languages)

    def _languages_for(self, language: str | None) -> Sequence[str]:
        """Put the language the caller asked for ahead of the configured ones.

        The providers each show the first language they can, so a request from a
        Russian UI only has to move ``rus`` to the front. An unrecognised code is
        ignored rather than rejected: falling back to the configured languages
        shows results, which is what the caller wanted.
        """

        requested = to_three_letter(language) if language else None
        if requested is None:
            return self._metadata_languages
        rest = tuple(
            configured
            for configured in self._metadata_languages
            if configured.strip().lower() != requested
        )
        return (requested, *rest)

    async def _search_both(
        self,
        term: str,
        languages: Sequence[str],
    ) -> list[MediaSearchResultDTO]:
        searches: list[tuple[MediaType, Coroutine[None, None, list[MediaSearchResultDTO]]]] = []
        if self._tvdb is not None:
            searches.append((MediaType.SERIES, self._search_series(term, languages)))
        if self._tmdb is not None:
            searches.append((MediaType.MOVIE, self._search_movies(term, languages)))
        if not searches:
            raise MetadataProviderUnavailableError(MediaType.SERIES, MediaType.MOVIE)

        outcomes = await asyncio.gather(
            *(search for _, search in searches),
            return_exceptions=True,
        )

        groups: list[list[MediaSearchResultDTO]] = []
        failures: list[BaseException] = []
        for (media_type, _), outcome in zip(searches, outcomes, strict=True):
            if isinstance(outcome, BaseException):
                # One provider being unreachable still leaves a useful search
                # over the other, so a failure only surfaces if nothing survived.
                self._logger.warning(
                    "Failed to search a metadata provider",
                    error=str(outcome),
                    media_type=media_type.value,
                    term=term,
                )
                failures.append(outcome)
                continue
            groups.append(outcome)

        if not groups:
            raise failures[0]
        return self._rank(term, groups)

    def _rank(
        self,
        term: str,
        groups: Sequence[Sequence[MediaSearchResultDTO]],
    ) -> list[MediaSearchResultDTO]:
        """Order a mixed result list so the closest titles come first.

        Each provider ranks its own hits, but the two rankings say nothing about
        each other, so titles are scored against the search term and a provider's
        own order breaks the ties.
        """

        ranked = [
            (self._title_score(result.title, term), rank, result)
            for group in groups
            for rank, result in enumerate(group)
        ]
        ranked.sort(key=lambda entry: (entry[0], entry[1]))
        return [result for _, _, result in ranked]

    def _title_score(self, title: str, term: str) -> int:
        candidate = title.casefold()
        wanted = term.casefold()
        if candidate == wanted:
            return 0
        if candidate.startswith(wanted):
            return 1
        if wanted in candidate:
            return 2
        return 3

    async def _search_series(
        self,
        term: str,
        languages: Sequence[str],
    ) -> list[MediaSearchResultDTO]:
        if self._tvdb is None:
            raise MetadataProviderUnavailableError(MediaType.SERIES)

        # The two searches answer different questions about the same term, so
        # they are issued together rather than one after the other.
        matches, lookups = await asyncio.gather(
            self._tvdb.search_series(term, languages=languages),
            self._safe_series_lookup(term),
        )
        library = {lookup.tvdb_id: lookup for lookup in lookups if lookup.existing_series_id}
        requested = await requested_seasons_by_series(self._repository)

        return [
            self._to_series_result(match, library.get(match.tvdb_id), requested)
            for match in matches
        ]

    async def _search_movies(
        self,
        term: str,
        languages: Sequence[str],
    ) -> list[MediaSearchResultDTO]:
        if self._tmdb is None:
            raise MetadataProviderUnavailableError(MediaType.MOVIE)

        matches, lookups = await asyncio.gather(
            self._tmdb.search_movies(term, languages=languages),
            self._safe_movie_lookup(term),
        )
        library = {lookup.tmdb_id: lookup for lookup in lookups if lookup.existing_movie_id}
        requested = await requested_movies(self._repository)

        return [
            self._to_movie_result(match, library.get(match.tmdb_id), requested) for match in matches
        ]

    def _to_series_result(
        self,
        match: TvdbSearchResult,
        lookup: SeriesLookup | None,
        requested: dict[int, dict[int, str]],
    ) -> MediaSearchResultDTO:
        library_id = lookup.existing_series_id if lookup else None
        seasons = requested.get(library_id, {}) if library_id else {}
        return MediaSearchResultDTO(
            media_type=MediaType.SERIES,
            provider_id=match.tvdb_id,
            title=match.name,
            year=match.year,
            overview=match.overview,
            poster_url=match.image_url,
            in_library=library_id is not None,
            library_id=library_id,
            requested_seasons=sorted(seasons),
        )

    def _to_movie_result(
        self,
        match: TmdbSearchResult,
        lookup: MovieLookup | None,
        requested: dict[int, MediaRequestRecord],
    ) -> MediaSearchResultDTO:
        library_id = lookup.existing_movie_id if lookup else None
        record = requested.get(library_id) if library_id else None
        return MediaSearchResultDTO(
            media_type=MediaType.MOVIE,
            provider_id=match.tmdb_id,
            title=match.title,
            year=match.year,
            overview=match.overview,
            poster_url=match.poster_url,
            in_library=library_id is not None,
            library_id=library_id,
            request_id=record.id if record else None,
            request_status=record.status if record else None,
        )

    async def _safe_series_lookup(self, term: str) -> list[SeriesLookup]:
        try:
            return await self._sonarr.search_series(term)
        except Exception as exc:  # pragma: no cover - defensive against HTTP failures
            self._logger.warning(
                "Failed to check Sonarr for search results",
                error=str(exc),
                term=term,
            )
            return []

    async def _safe_movie_lookup(self, term: str) -> list[MovieLookup]:
        try:
            return await self._radarr.search_movies(term)
        except Exception as exc:  # pragma: no cover - defensive against HTTP failures
            self._logger.warning(
                "Failed to check Radarr for search results",
                error=str(exc),
                term=term,
            )
            return []


__all__ = ["SearchMediaUseCase"]
