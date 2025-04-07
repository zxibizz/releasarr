from __future__ import annotations

import asyncio

import loguru

from src.application.use_cases.releases.export_finished_series import (
    UseCase_ExportFinishedSeries,
)
from src.application.use_cases.releases.import_torrent_stats import (
    UseCase_ImportReleasesTorrentStats,
)
from src.application.use_cases.releases.re_grab_outdated import (
    UseCase_ReGrabOutdatedReleases,
)
from src.application.use_cases.shows.sync_missing_series import (
    UseCase_SyncMissingSeries,
)


class TaskScheduler:
    def __init__(
        self,
        sync_missing_series: UseCase_SyncMissingSeries,
        import_releases_torrent_stats: UseCase_ImportReleasesTorrentStats,
        export_finished_series: UseCase_ExportFinishedSeries,
        re_grab_outdated_releases: UseCase_ReGrabOutdatedReleases,
        logger: loguru.Logger,
    ) -> None:
        self.sync_missing_series = sync_missing_series
        self.import_releases_torrent_stats = import_releases_torrent_stats
        self.export_finished_series = export_finished_series
        self.re_grab_outdated_releases = re_grab_outdated_releases
        self.logger = logger

        self._stop = False
        self._run_sync_task = False
        self._wait_tasks = []
        self._cancel_tasks = []

    async def start(self) -> None:
        self.logger.info("Started")

        with self.logger.catch(reraise=True):
            self._cancel_tasks.append(
                asyncio.create_task(self.enable_sync_task_schedule())
            )
            self._wait_tasks.append(asyncio.create_task(self.start_sync_task()))

    async def stop(self) -> None:
        self.logger.info("Stopping")
        self._stop = True
        for task in self._cancel_tasks:
            task.cancel()
        with self.logger.catch(reraise=True):
            await asyncio.gather(*self._wait_tasks)

    async def enable_sync_task_schedule(self):
        while True:
            self._run_sync_task = True
            await asyncio.sleep(60 * 60)

    async def start_sync_task(self):
        while self._stop is False:
            if not self._run_sync_task:
                await asyncio.sleep(5)
                continue
            await self.sync_task()

    async def trigger_sync_task(self, after: int = 0):
        if after == 0:
            self._run_sync_task = True
            return

        async def _inner():
            await asyncio.sleep(after)
            self._run_sync_task = True

        asyncio.create_task(_inner())

    async def sync_task(self):
        with self.logger.catch(reraise=True):
            self.logger.info("Running full sync")

            try:
                await self.sync_missing_series.process()
                await self.import_releases_torrent_stats.process()
                export_finished_series_result = (
                    await self.export_finished_series.process()
                )
                if export_finished_series_result.failed > 0:
                    self.logger.warning(
                        f"We have {export_finished_series_result.failed} releases failed to export! "
                        "Rescheduling the sync..."
                    )
                    self.trigger_sync_task(after=10)

                await self.re_grab_outdated_releases.process()

                self._run_sync_task = False
                self.logger.info("Full sync finished")
            except Exception:
                self.logger.exception("Failed full sync")
