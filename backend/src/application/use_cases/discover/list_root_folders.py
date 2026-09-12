"""List the library locations a request can be added to."""

from __future__ import annotations

from src.application.interfaces.radarr import RadarrService
from src.application.interfaces.sonarr import SonarrService
from src.application.use_cases.discover.dto import RootFolderDTO
from src.domain.enums import MediaType


class ListRootFoldersUseCase:
    """Return the root folders configured in Sonarr or Radarr."""

    def __init__(
        self,
        *,
        sonarr_service: SonarrService,
        radarr_service: RadarrService,
    ) -> None:
        self._sonarr = sonarr_service
        self._radarr = radarr_service

    async def execute(self, media_type: MediaType) -> list[RootFolderDTO]:
        if media_type == MediaType.SERIES:
            folders = await self._sonarr.get_root_folders()
        else:
            folders = await self._radarr.get_root_folders()

        # An unreachable folder would fail the add, so it is not offered.
        return [
            RootFolderDTO(path=folder.path, free_space=folder.free_space)
            for folder in folders
            if folder.accessible
        ]


__all__ = ["ListRootFoldersUseCase"]
