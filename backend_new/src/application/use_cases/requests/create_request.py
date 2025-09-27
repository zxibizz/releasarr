"""Create media requests."""

from __future__ import annotations

from uuid import uuid4

from src.application.interfaces.media_requests import (
    CreateMediaRequestData,
    MediaLocalization,
    MediaRequestRepository,
)
from src.application.use_cases.requests.commands import (
    CreateMediaRequestCommand,
    CreateMovieRequestCommand,
    CreateSeriesRequestCommand,
)
from src.application.use_cases.requests.dto import MediaRequestDTO
from src.application.use_cases.requests.mappers import record_to_dto
from src.domain.enums import MediaRequestStatus, MediaType


class CreateMediaRequestUseCase:
    """Use case responsible for creating new media requests."""

    def __init__(self, repository: MediaRequestRepository) -> None:
        self._repository = repository

    async def execute(self, command: CreateMediaRequestCommand) -> MediaRequestDTO:
        request_id = uuid4().hex

        if isinstance(command, CreateMovieRequestCommand):
            data = self._build_movie_data(request_id, command)
        else:
            data = self._build_series_data(request_id, command)

        record = await self._repository.create_request(data)
        return record_to_dto(record)

    def _build_movie_data(
        self,
        request_id: str,
        command: CreateMovieRequestCommand,
    ) -> CreateMediaRequestData:
        genres = self._normalise_genres(command.genres)
        localizations = self._normalise_localizations(command.localizations)
        return CreateMediaRequestData(
            id=request_id,
            media_type=MediaType.MOVIE,
            title=command.title,
            year=command.year,
            overview=command.overview,
            poster_url=command.poster_url,
            genres=genres,
            runtime_minutes=command.runtime,
            imdb_id=command.imdb_id,
            season_number=None,
            total_episodes=None,
            series_title=None,
            series_year=None,
            status=MediaRequestStatus.PENDING,
            sonarr_series_id=None,
            localizations=localizations,
        )

    def _build_series_data(
        self,
        request_id: str,
        command: CreateSeriesRequestCommand,
    ) -> CreateMediaRequestData:
        genres = self._normalise_genres(command.genres)
        localizations = self._normalise_localizations(command.localizations)
        return CreateMediaRequestData(
            id=request_id,
            media_type=MediaType.SERIES,
            title=command.title,
            year=command.year,
            overview=command.overview,
            poster_url=command.poster_url,
            genres=genres,
            runtime_minutes=None,
            imdb_id=command.imdb_id,
            season_number=command.season_number,
            total_episodes=command.total_episodes,
            series_title=command.series_title,
            series_year=command.series_year,
            status=MediaRequestStatus.PENDING,
            sonarr_series_id=None,
            localizations=localizations,
        )

    def _normalise_genres(self, genres: list[str] | None) -> list[str]:
        if not genres:
            return []
        return [genre for genre in genres if genre]

    def _normalise_localizations(
        self,
        localizations: dict[str, MediaLocalization] | None,
    ) -> dict[str, MediaLocalization]:
        if not localizations:
            return {}
        result: dict[str, MediaLocalization] = {}
        for language, localization in localizations.items():
            if not language:
                continue
            language_key = language.lower()
            result[language_key] = MediaLocalization(
                title=localization.title or None,
                overview=localization.overview or None,
            )
        return result


__all__ = ["CreateMediaRequestUseCase"]
