"""Delete releases by identifier."""

from __future__ import annotations

from src.application.interfaces.releases import ReleaseDownloadService, ReleaseRepository
from src.application.use_cases.releases.exceptions import ReleaseNotFoundError
from src.core.logging import get_logger


class DeleteReleaseUseCase:
    """Use case removing a release and its associated files."""

    def __init__(
        self,
        repository: ReleaseRepository,
        download_service: ReleaseDownloadService,
    ) -> None:
        self._repository = repository
        self._download_service = download_service
        self._logger = get_logger(component="delete_release")

    async def execute(self, release_id: str) -> None:
        release = await self._repository.get_release(release_id)
        if release:
            try:
                await self._download_service.delete_download(release.info_hash)
            except Exception:
                self._logger.warning(
                    "Failed to delete release from downloader",
                    release_id=release_id,
                    info_hash=release.info_hash,
                )

        deleted = await self._repository.delete_release(release_id)
        if not deleted:
            raise ReleaseNotFoundError(release_id)


__all__ = ["DeleteReleaseUseCase"]
