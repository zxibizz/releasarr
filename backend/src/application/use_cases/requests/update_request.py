"""Partially update media requests."""

from __future__ import annotations

from src.application.interfaces.media_requests import (
    MediaLocalization,
    MediaRequestRepository,
    UpdateMediaRequestData,
)
from src.application.use_cases.requests.commands import UNSET, UpdateMediaRequestCommand
from src.application.use_cases.requests.dto import MediaRequestDTO
from src.application.use_cases.requests.exceptions import (
    EmptyUpdatePayloadError,
    MediaRequestNotFoundError,
)
from src.application.use_cases.requests.mappers import record_to_dto


class UpdateMediaRequestUseCase:
    """Use case responsible for applying partial media request updates."""

    def __init__(self, repository: MediaRequestRepository) -> None:
        self._repository = repository

    async def execute(self, request_id: str, command: UpdateMediaRequestCommand) -> MediaRequestDTO:
        if command.is_empty():
            raise EmptyUpdatePayloadError()

        data = UpdateMediaRequestData()

        if command.title is not UNSET:
            data.title = command.title
        if command.year is not UNSET:
            data.year = command.year
        if command.poster_url is not UNSET:
            data.poster_url = command.poster_url
        if command.overview is not UNSET:
            data.overview = command.overview
        if command.genres is not UNSET:
            data.genres = self._normalise_genres(command.genres)
        if command.status is not UNSET:
            data.status = command.status
        if command.runtime is not UNSET:
            data.runtime_minutes = command.runtime
        if command.imdb_id is not UNSET:
            data.imdb_id = command.imdb_id
        if command.season_number is not UNSET:
            data.season_number = command.season_number
        if command.total_episodes is not UNSET:
            data.total_episodes = command.total_episodes
        if command.series_title is not UNSET:
            data.series_title = command.series_title
        if command.series_year is not UNSET:
            data.series_year = command.series_year
        if command.localizations is not UNSET:
            data.localizations = self._normalise_localizations(command.localizations)

        record = await self._repository.update_request(request_id, data)
        if record is None:
            raise MediaRequestNotFoundError(request_id)

        return record_to_dto(record)

    def _normalise_genres(self, genres: list[str] | None) -> list[str]:
        if genres is None:
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
            key = language.lower()
            result[key] = MediaLocalization(
                title=localization.title or None,
                overview=localization.overview or None,
            )
        return result


__all__ = ["UpdateMediaRequestUseCase"]
