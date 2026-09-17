"""Recompute a media request's derived state after any release-lifecycle change."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from loguru._logger import Logger

from src.application.interfaces.media_requests import (
    MediaRequestRepository,
    UpdateMediaRequestData,
)
from src.application.interfaces.releases import ReleaseRecord, ReleaseRepository
from src.application.use_cases.releases.warnings import RequestWarningSynchronizer
from src.application.use_cases.requests.state import ArrCompletion, RequestStateDeriver
from src.application.utility.sentinels import UNSET
from src.core.logging import get_logger
from src.domain.enums import LogComponent


@dataclass(slots=True)
class RecomputeRequestStateResult:
    """Summary of a recompute pass."""

    updated: int = 0
    warnings_synced: int = 0


class RecomputeRequestStateUseCase:
    """Single entry point for settling a request's status, freshness and warnings.

    Every release-lifecycle use case (grab, delete, remap, regrab, export, the
    scheduled release sync) calls this instead of writing status or warnings
    itself, so there is exactly one place that decides what a request's
    releases imply.
    """

    def __init__(
        self,
        *,
        repository: MediaRequestRepository,
        release_repository: ReleaseRepository,
        warning_synchronizer: RequestWarningSynchronizer,
        deriver: RequestStateDeriver,
        logger: Logger | None = None,
    ) -> None:
        self._repository = repository
        self._release_repository = release_repository
        self._warning_synchronizer = warning_synchronizer
        self._deriver = deriver
        self._logger = logger or get_logger(LogComponent.USECASE_RECOMPUTE_STATE)

    async def execute(
        self,
        request_ids: Sequence[str],
        *,
        arr_completion: Mapping[str, ArrCompletion] | None = None,
    ) -> RecomputeRequestStateResult:
        ids = sorted({request_id for request_id in request_ids if request_id})
        result = RecomputeRequestStateResult()
        if not ids:
            return result

        releases_by_request = await self._group_releases_by_request(ids)

        for request_id in ids:
            record = await self._repository.get_request(request_id)
            if record is None:
                continue

            arr = arr_completion.get(request_id) if arr_completion else None
            derived = self._deriver.derive(record, releases_by_request[request_id], arr)

            update = UpdateMediaRequestData()
            changed = False
            if derived.status is not UNSET and derived.status != record.status:
                update.status = derived.status
                changed = True
            if derived.newest_release_published_at != record.newest_release_published_at:
                update.newest_release_published_at = derived.newest_release_published_at
                changed = True

            if not changed:
                continue

            await self._repository.update_request(request_id, update)
            result.updated += 1
            if update.status is not UNSET:
                self._logger.info(
                    "Request status changed",
                    request_id=request_id,
                    previous_status=record.status.value,
                    status=derived.status.value,
                )

        await self._warning_synchronizer.sync_for_requests(ids)
        result.warnings_synced = len(ids)
        return result

    async def _group_releases_by_request(
        self,
        request_ids: Sequence[str],
    ) -> dict[str, list[ReleaseRecord]]:
        by_request: dict[str, list[ReleaseRecord]] = {request_id: [] for request_id in request_ids}
        wanted = set(request_ids)
        for release in await self._release_repository.get_releases_for_requests(list(request_ids)):
            for request_id in release.request_ids:
                if request_id in wanted:
                    by_request[request_id].append(release)
        return by_request


__all__ = ["RecomputeRequestStateResult", "RecomputeRequestStateUseCase"]
