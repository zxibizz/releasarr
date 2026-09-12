"""Add media to Sonarr/Radarr and turn it into media requests."""

from __future__ import annotations

from dataclasses import dataclass, field

from loguru._logger import Logger

from src.application.interfaces.media_requests import MediaRequestRepository
from src.application.interfaces.radarr import RadarrService
from src.application.interfaces.sonarr import SonarrService
from src.application.use_cases.discover.exceptions import (
    InvalidRootFolderError,
    MediaNotFoundError,
    NoQualityProfileError,
    SeasonSelectionError,
)
from src.application.use_cases.requests.dto import MediaRequestDTO
from src.application.use_cases.requests.mappers import record_to_dto
from src.application.use_cases.requests.sync_radarr import SyncRadarrMediaRequestsUseCase
from src.application.use_cases.requests.sync_sonarr import SyncSonarrMediaRequestsUseCase
from src.core.logging import get_logger
from src.domain.enums import MediaType


@dataclass(slots=True)
class AddMediaRequestCommand:
    """A picked search result, plus where and what to add of it."""

    media_type: MediaType
    provider_id: int
    root_folder_path: str
    season_numbers: list[int] = field(default_factory=list)


class AddMediaRequestUseCase:
    """Add a series or movie to the library and return its media requests.

    The requests are built by the same code the recurring sync uses, driven for
    the one series or movie just added, so an added item is described exactly as
    a synced one is. That runs before returning, which is what lets the caller
    show the request it just created rather than an empty list to poll.
    """

    def __init__(
        self,
        *,
        repository: MediaRequestRepository,
        sonarr_service: SonarrService,
        radarr_service: RadarrService,
        sync_sonarr: SyncSonarrMediaRequestsUseCase,
        sync_radarr: SyncRadarrMediaRequestsUseCase,
        sonarr_quality_profile_id: int | None = None,
        radarr_quality_profile_id: int | None = None,
        logger: Logger | None = None,
    ) -> None:
        self._repository = repository
        self._sonarr = sonarr_service
        self._radarr = radarr_service
        self._sync_sonarr = sync_sonarr
        self._sync_radarr = sync_radarr
        self._sonarr_quality_profile_id = sonarr_quality_profile_id
        self._radarr_quality_profile_id = radarr_quality_profile_id
        self._logger = logger or get_logger(component="add_media_request")

    async def execute(self, command: AddMediaRequestCommand) -> list[MediaRequestDTO]:
        if command.media_type == MediaType.SERIES:
            return await self._add_series(command)
        return await self._add_movie(command)

    async def _add_series(self, command: AddMediaRequestCommand) -> list[MediaRequestDTO]:
        seasons = sorted(set(command.season_numbers))
        if not seasons:
            raise SeasonSelectionError("At least one season must be selected")

        lookup = await self._sonarr.lookup_series(command.provider_id)
        if lookup is None:
            raise MediaNotFoundError(MediaType.SERIES, command.provider_id)

        unknown = [season for season in seasons if season not in lookup.season_numbers]
        if unknown and lookup.season_numbers:
            missing = ", ".join(str(season) for season in unknown)
            raise SeasonSelectionError(f"'{lookup.title}' has no season {missing}")

        series_id = lookup.existing_series_id
        if series_id is None:
            await self._validate_root_folder(MediaType.SERIES, command.root_folder_path)
            series_id = await self._sonarr.add_series(
                tvdb_id=command.provider_id,
                root_folder_path=command.root_folder_path,
                quality_profile_id=await self._resolve_quality_profile(MediaType.SERIES),
                monitored_seasons=seasons,
            )
        else:
            # Already in the library, so the root folder is Sonarr's to keep and
            # only the season monitoring needs widening.
            await self._sonarr.set_season_monitoring(series_id, seasons)

        # A series added a moment ago has no episodes yet, and a request built
        # now would record every one of its seasons as empty.
        await self._sonarr.wait_for_series_episodes(series_id, seasons)

        request_ids = await self._sync_sonarr.sync_series(series_id, seasons)
        self._logger.info(
            "Added series requests",
            tvdb_id=command.provider_id,
            sonarr_series_id=series_id,
            seasons=seasons,
            requests=len(request_ids),
        )
        return await self._load_requests(request_ids)

    async def _add_movie(self, command: AddMediaRequestCommand) -> list[MediaRequestDTO]:
        if command.season_numbers:
            raise SeasonSelectionError("Movies have no seasons to select")

        lookup = await self._radarr.lookup_movie(command.provider_id)
        if lookup is None:
            raise MediaNotFoundError(MediaType.MOVIE, command.provider_id)

        movie_id = lookup.existing_movie_id
        if movie_id is None:
            await self._validate_root_folder(MediaType.MOVIE, command.root_folder_path)
            movie_id = await self._radarr.add_movie(
                tmdb_id=command.provider_id,
                root_folder_path=command.root_folder_path,
                quality_profile_id=await self._resolve_quality_profile(MediaType.MOVIE),
            )
        else:
            await self._radarr.set_movie_monitored(movie_id)

        request_id = await self._sync_radarr.sync_movie_by_id(movie_id)
        self._logger.info(
            "Added movie request",
            tmdb_id=command.provider_id,
            radarr_movie_id=movie_id,
            request_id=request_id,
        )
        return await self._load_requests([request_id] if request_id else [])

    async def _resolve_quality_profile(self, media_type: MediaType) -> int:
        """Pick the quality profile to add against.

        Releasarr never grabs by profile - it searches indexers itself - but both
        *arr apps refuse an add without one, so a configured id is honoured and
        otherwise the first profile they report is used.
        """

        if media_type == MediaType.SERIES:
            configured = self._sonarr_quality_profile_id
            profiles = None if configured else await self._sonarr.get_quality_profiles()
        else:
            configured = self._radarr_quality_profile_id
            profiles = None if configured else await self._radarr.get_quality_profiles()

        if configured:
            return configured
        if not profiles:
            raise NoQualityProfileError(media_type)
        return profiles[0].id

    async def _validate_root_folder(self, media_type: MediaType, root_folder_path: str) -> None:
        if media_type == MediaType.SERIES:
            folders = await self._sonarr.get_root_folders()
        else:
            folders = await self._radarr.get_root_folders()
        if not any(folder.path == root_folder_path for folder in folders):
            raise InvalidRootFolderError(root_folder_path)

    async def _load_requests(self, request_ids: list[str]) -> list[MediaRequestDTO]:
        requests: list[MediaRequestDTO] = []
        for request_id in request_ids:
            record = await self._repository.get_request(request_id)
            if record is not None:
                requests.append(record_to_dto(record))
        return requests


__all__ = ["AddMediaRequestCommand", "AddMediaRequestUseCase"]
