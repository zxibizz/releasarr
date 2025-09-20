from __future__ import annotations

import asyncio

from loguru import logger

from app.services.export_finished import FinishedReleaseExportService
from app.services.missing_series import MissingSeriesSyncService
from app.services.regrab_releases import OutdatedReleaseRegrabService
from app.services.torrent_stats import TorrentStatsImportService


class TaskScheduler:
    def __init__(self) -> None:
        self.missing_series_sync = MissingSeriesSyncService()
        self.torrent_stats_import = TorrentStatsImportService()
        self.export_finished = FinishedReleaseExportService()
        self.regrab_outdated = OutdatedReleaseRegrabService()

        self._stop = False
        self._run_sync = False
        self._wait_tasks: list[asyncio.Task] = []
        self._schedule_task: asyncio.Task | None = None

    async def start(self) -> None:
        logger.info("Task scheduler started")
        self._run_sync = True
        self._schedule_task = asyncio.create_task(self._enable_sync_task_schedule())
        self._wait_tasks.append(asyncio.create_task(self._sync_loop()))

    async def stop(self) -> None:
        logger.info("Stopping task scheduler")
        self._stop = True
        if self._schedule_task:
            self._schedule_task.cancel()
        if self._wait_tasks:
            await asyncio.gather(*self._wait_tasks, return_exceptions=True)

    async def trigger_sync(self, after: int = 0) -> None:
        async def _inner(delay: int) -> None:
            await asyncio.sleep(delay)
            self._run_sync = True

        asyncio.create_task(_inner(after))

    async def _enable_sync_task_schedule(self) -> None:
        while True:
            self._run_sync = True
            await asyncio.sleep(60 * 60)

    async def _sync_loop(self) -> None:
        while not self._stop:
            if not self._run_sync:
                await asyncio.sleep(5)
                continue
            await self._run_full_sync()
            self._run_sync = False

    async def _run_full_sync(self) -> None:
        logger.info("Running scheduled maintenance tasks")
        try:
            await self.missing_series_sync.run()
            await self.torrent_stats_import.run()
            await self.export_finished.run()
            await self.regrab_outdated.run()
        except Exception:  # pragma: no cover - diagnostics only
            logger.exception("Scheduled task failed")
            await self.trigger_sync(after=30)
        else:
            logger.info("Scheduled maintenance completed")
