"""The individual units of sync work.

Shared by the periodic scheduler loops and the on-demand job runner so both
paths perform identical work and report it the same way.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from loguru import logger

from src.core.container import AppContainer
from src.domain.enums import SyncJobKind
from src.tasks.sync_releases import SyncReleasesTask

StepSummary = dict[str, object]


@dataclass(slots=True)
class SyncSteps:
    """Runs a single sync step against the shared application container."""

    container: AppContainer
    _locks: dict[SyncJobKind, asyncio.Lock] = field(default_factory=dict)

    def for_kind(self, kind: SyncJobKind) -> Callable[[], Awaitable[StepSummary]]:
        """The callable implementing ``kind``, tagged for the logs view.

        Every path that runs a task goes through here, so binding the task name
        once means anything logged underneath it — including the use cases
        several layers down — can be filtered by task without each call site
        having to remember to pass it.
        """

        step = getattr(self, _STEP_METHODS[kind])
        lock = self._locks.setdefault(kind, asyncio.Lock())

        async def run() -> StepSummary:
            # The periodic loops and the queued-job runner share this instance,
            # so both can reach one task at once: an export waiting on Sonarr
            # leaves a window wide enough for the next scheduled run to start on
            # the releases it is still importing, and they duplicate each other's
            # work. Later arrivals queue rather than being dropped, so a manual
            # trigger still runs - it just finds the work already done.
            async with lock:
                # contextualize is contextvar-based, so concurrent task loops each
                # keep their own value instead of overwriting a shared one.
                with logger.contextualize(task=kind.value):
                    return await step()

        return run

    async def sonarr_sync(self) -> StepSummary:
        """Import Sonarr's missing seasons into media requests."""

        result = await self.container.use_cases.media_requests.sync_sonarr.execute()
        return {
            "created": result.created,
            "updated": result.updated,
            "completed": result.completed,
        }

    async def release_sync(self) -> StepSummary:
        """Refresh download state for every tracked release from qBittorrent."""

        client = self.container.services.qbittorrent_client
        if client is None:
            return {"skipped": True, "reason": "qbittorrent_not_configured"}

        task = SyncReleasesTask(
            db=self.container.db_manager,
            client=client,
            category=self.container.settings.qbittorrent_category,
        )
        result = await task.execute()
        return {
            "synced": result.synced,
            "failed": result.failed,
            "not_found": result.not_found,
            "requests_updated": result.requests_updated,
        }

    async def export(self) -> StepSummary:
        """Import finished releases into Sonarr."""

        result = await self.container.use_cases.releases.export_finished.execute()
        return {"succeeded": result.succeeded, "failed": result.failed}

    async def regrab(self) -> StepSummary:
        """Re-download releases the indexer has since replaced (e.g. repacks)."""

        await self.container.use_cases.releases.regrab_outdated.execute()
        return {"completed": True}


_STEP_METHODS: dict[SyncJobKind, str] = {
    SyncJobKind.SONARR_SYNC: "sonarr_sync",
    SyncJobKind.RELEASE_SYNC: "release_sync",
    SyncJobKind.EXPORT: "export",
    SyncJobKind.REGRAB: "regrab",
}


__all__ = ["StepSummary", "SyncSteps"]
