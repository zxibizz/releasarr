"""Resolve what happens to a request's other releases when a new one is grabbed."""

from __future__ import annotations

from loguru import logger

from src.application.interfaces.releases import (
    ReleaseDownloadService,
    ReleaseRecord,
    ReleaseRepository,
)
from src.application.interfaces.request_warnings import RequestWarningRepository
from src.application.use_cases.requests.recompute_state import RecomputeRequestStateUseCase


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
        warning_repository: RequestWarningRepository,
        recompute_state: RecomputeRequestStateUseCase,
    ) -> None:
        self._repository = repository
        self._download_service = download_service
        self._warning_repository = warning_repository
        self._recompute_state = recompute_state

    async def existing_for(self, request_id: str) -> list[ReleaseRecord]:
        """Releases already linked to this request, before a new grab is added."""

        return await self._repository.get_releases_for_requests([request_id])

    async def replace(self, request_id: str, existing: list[ReleaseRecord]) -> None:
        for release in existing:
            if release.request_ids == [request_id]:
                await self._delete(release)
            else:
                await self._repository.unlink_request(release.id, request_id)
                await self._clear_unlinked(request_id, release.id)

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
        await self._clear_deleted(release)

    async def _clear_unlinked(self, request_id: str, release_id: str) -> None:
        try:
            await self._warning_repository.delete_for_request_release(request_id, release_id)
            # Only this request's release set changed; the release's other
            # requests are unaffected by losing this one link.
            await self._recompute_state.execute([request_id])
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning(
                "Failed to settle request for an unlinked release",
                release_id=release_id,
                request_id=request_id,
                error=str(exc),
            )

    async def _clear_deleted(self, release: ReleaseRecord) -> None:
        try:
            await self._warning_repository.delete_for_release(release.id)
            await self._recompute_state.execute(release.request_ids)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning(
                "Failed to settle requests for a replaced release",
                release_id=release.id,
                error=str(exc),
            )


__all__ = ["ExistingReleaseReplacer"]
