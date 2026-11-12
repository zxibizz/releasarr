"""Read and change the root folder a request's series or movie lives in."""

from __future__ import annotations

from dataclasses import dataclass

from loguru._logger import Logger

from src.application.interfaces.arr import ArrRootFolder
from src.application.interfaces.media_requests import MediaRequestRepository
from src.application.interfaces.radarr import RadarrService
from src.application.interfaces.sonarr import SonarrService
from src.application.use_cases.discover.dto import LibraryFolderDTO
from src.application.use_cases.discover.exceptions import (
    DisallowedRootFolderError,
    InvalidRootFolderError,
    LibraryFolderUnavailableError,
)
from src.application.use_cases.requests.exceptions import MediaRequestNotFoundError
from src.core.logging import get_logger
from src.domain.enums import LogComponent, MediaType


@dataclass(slots=True)
class MoveLibraryFolderCommand:
    """The root folder a request's media should move to, and who is asking."""

    root_folder_path: str
    # None means the caller is unrestricted; see allowed_root_folders().
    allowed_root_folders: list[str] | None = None


def _normalise(path: str) -> str:
    return path.rstrip("/\\") or path


def _configured_root(path: str | None, folders: list[ArrRootFolder]) -> str | None:
    """The configured root folder ``path`` is, or sits under, spelled as the *arr spells it.

    The *arr reports a root folder with or without a trailing separator depending
    on how it was entered, and the picker matches the current folder against the
    configured ones by string, so the answer is always one of theirs.
    """

    if not path:
        return None
    target = _normalise(path)
    best: str | None = None
    for folder in folders:
        root = _normalise(folder.path)
        if (target == root or target.startswith(f"{root}/")) and (
            best is None or len(root) > len(_normalise(best))
        ):
            best = folder.path
    return best


class _LibraryFolderBase:
    def __init__(
        self,
        *,
        repository: MediaRequestRepository,
        sonarr_service: SonarrService,
        radarr_service: RadarrService,
    ) -> None:
        self._repository = repository
        self._sonarr = sonarr_service
        self._radarr = radarr_service

    async def _resolve(self, request_id: str) -> tuple[MediaType, int]:
        """The *arr item behind a request.

        A request only carries the Sonarr or Radarr id once the sync has seen
        its media in the library, and before that there is nothing to move.
        """

        record = await self._repository.get_request(request_id)
        if record is None:
            raise MediaRequestNotFoundError(request_id)
        library_id = (
            record.sonarr_series_id
            if record.media_type == MediaType.SERIES
            else record.radarr_movie_id
        )
        if library_id is None:
            app = "Sonarr" if record.media_type == MediaType.SERIES else "Radarr"
            raise LibraryFolderUnavailableError(
                f"Request '{request_id}' is not linked to anything in {app} yet"
            )
        return record.media_type, library_id

    async def _root_folders(self, media_type: MediaType) -> list[ArrRootFolder]:
        if media_type == MediaType.SERIES:
            return await self._sonarr.get_root_folders()
        return await self._radarr.get_root_folders()

    async def _describe(
        self, media_type: MediaType, library_id: int, folders: list[ArrRootFolder]
    ) -> LibraryFolderDTO:
        if media_type == MediaType.SERIES:
            series = await self._sonarr.get_series(library_id)
            path, reported_root = series.path, series.root_folder_path
        else:
            movie = await self._radarr.get_movie(library_id)
            path, reported_root = movie.path, movie.root_folder_path
        return LibraryFolderDTO(
            media_type=media_type,
            path=path,
            root_folder_path=_configured_root(reported_root, folders)
            or _configured_root(path, folders)
            or reported_root,
        )


class GetLibraryFolderUseCase(_LibraryFolderBase):
    """Answer which root folder a request's series or movie is stored in."""

    async def execute(self, request_id: str) -> LibraryFolderDTO:
        media_type, library_id = await self._resolve(request_id)
        folders = await self._root_folders(media_type)
        return await self._describe(media_type, library_id, folders)


class MoveLibraryFolderUseCase(_LibraryFolderBase):
    """Move a request's series or movie, files and all, to another root folder.

    A root folder is what a media server library is pointed at, so picking the
    wrong one at add time puts a title in front of the wrong audience; this is
    the way back that does not involve Sonarr's or Radarr's own UI.

    The move is of the whole series, not of the season the request covers:
    Sonarr keeps one folder per series, and every season's request moves with it.

    A restricted caller has to be allowed both folders. The destination for the
    obvious reason, and the source because moving a title out of a library they
    may not add to is taking it away from whoever that library is for.
    """

    def __init__(
        self,
        *,
        repository: MediaRequestRepository,
        sonarr_service: SonarrService,
        radarr_service: RadarrService,
        logger: Logger | None = None,
    ) -> None:
        super().__init__(
            repository=repository, sonarr_service=sonarr_service, radarr_service=radarr_service
        )
        self._logger = logger or get_logger(LogComponent.USECASE_MOVE_LIBRARY_FOLDER)

    async def execute(self, request_id: str, command: MoveLibraryFolderCommand) -> LibraryFolderDTO:
        media_type, library_id = await self._resolve(request_id)
        folders = await self._root_folders(media_type)

        target = next(
            (
                folder
                for folder in folders
                if _normalise(folder.path) == _normalise(command.root_folder_path)
            ),
            None,
        )
        if target is None or not target.accessible:
            raise InvalidRootFolderError(command.root_folder_path)

        allowed = command.allowed_root_folders
        if allowed is not None and target.path not in allowed:
            raise DisallowedRootFolderError(target.path)

        current = await self._describe(media_type, library_id, folders)
        if allowed is not None and current.root_folder_path not in allowed:
            raise DisallowedRootFolderError(current.root_folder_path or current.path or "")

        if current.root_folder_path == target.path:
            return current

        if media_type == MediaType.SERIES:
            await self._sonarr.move_series(library_id, target.path)
        else:
            await self._radarr.move_movie(library_id, target.path)

        self._logger.info(
            "Moved to another root folder",
            request_id=request_id,
            media_type=media_type.value,
            library_id=library_id,
            source=current.root_folder_path,
            destination=target.path,
        )

        # The *arr rewrites the path before it answers and moves the files
        # behind it, so reading back reports where the title now lives.
        return await self._describe(media_type, library_id, folders)


__all__ = [
    "GetLibraryFolderUseCase",
    "MoveLibraryFolderCommand",
    "MoveLibraryFolderUseCase",
]
