"""Resolve what happens to a request's other releases when a new one is grabbed."""

from __future__ import annotations

from loguru import logger

from src.application.interfaces.releases import (
    ReleaseDownloadService,
    ReleaseRecord,
    ReleaseRepository,
)


class ExistingReleaseReplacer:
    """Apply the user's keep/replace decision to a request's existing releases.

    A release grabbed only for this request is torn down entirely, torrent
    included. A release shared with other requests (a multi-season pack) only
    loses its link to this one - the other requests still need it.
    """

    def __init__(
        self,
        repository: ReleaseRepository,
        download_service: ReleaseDownloadService,
    ) -> None:
        self._repository = repository
        self._download_service = download_service

    async def existing_for(self, request_id: str) -> list[ReleaseRecord]:
        """Releases already linked to this request, before a new grab is added."""

        return await self._repository.get_releases_for_requests([request_id])

    async def replace(self, request_id: str, existing: list[ReleaseRecord]) -> None:
        for release in existing:
            if release.request_ids == [request_id]:
                await self._delete(release)
            else:
                await self._repository.unlink_request(release.id, request_id)

    async def _delete(self, release: ReleaseRecord) -> None:
        try:
            await self._download_service.delete_download(release.info_hash)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning(
                "Failed to delete replaced release from downloader",
                release_id=release.id,
                info_hash=release.info_hash,
                error=str(exc),
            )
        await self._repository.delete_release(release.id)


__all__ = ["ExistingReleaseReplacer"]
