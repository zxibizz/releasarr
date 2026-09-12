"""Standalone background worker that runs periodic sync/export tasks.

This is intentionally a separate process entrypoint (run via
``python -m src.tasks.scheduler_service``) and is never started inside the
FastAPI app, honouring the "no implicit background schedulers in the web app"
architecture principle. It reuses the shared application container so it picks
up the same settings, logging, and clients as the API.
"""

from __future__ import annotations

import asyncio
import signal

from loguru import logger

from src.core.container import AppContainer, get_container
from src.tasks.sync_releases import SyncReleasesTask

SONARR_SYNC_INTERVAL = 60 * 60
RELEASE_SYNC_INTERVAL = 30
EXPORT_INTERVAL = 5 * 60
REGRAB_INTERVAL = 60 * 60


class SchedulerService:
    """Runs the periodic background tasks concurrently until shutdown."""

    def __init__(self, container: AppContainer | None = None) -> None:
        self._shutdown = False
        self.container = container or get_container()
        self.container.startup()
        self.logger = logger.bind(service="Scheduler")

    async def start(self) -> None:
        self.logger.info("Starting scheduler service")

        tasks = [
            asyncio.create_task(self._run_sonarr_sync_loop()),
            asyncio.create_task(self._run_release_sync_loop()),
            asyncio.create_task(self._run_export_loop()),
            asyncio.create_task(self._run_regrab_loop()),
        ]

        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            self.logger.info("Scheduler tasks cancelled")
        finally:
            await self.shutdown()

    async def shutdown(self) -> None:
        self.logger.info("Shutting down scheduler service")
        self._shutdown = True
        await self.container.shutdown()

    async def _run_sonarr_sync_loop(self) -> None:
        while not self._shutdown:
            try:
                use_case = self.container.use_cases.media_requests.sync_sonarr
                result = await use_case.execute()
                self.logger.info(
                    "Sonarr sync complete "
                    f"(created={result.created}, updated={result.updated}, "
                    f"completed={result.completed})"
                )
            except Exception as exc:
                self.logger.exception(f"Sonarr sync failed: {exc}")
            await self._sleep(SONARR_SYNC_INTERVAL)

    async def _run_release_sync_loop(self) -> None:
        client = self.container.services.qbittorrent_client
        if client is None:
            self.logger.warning("qBittorrent not configured; release sync disabled")
            return

        while not self._shutdown:
            try:
                task = SyncReleasesTask(
                    db=self.container.db_manager,
                    client=client,
                    category=self.container.settings.qbittorrent_category,
                )
                result = await task.execute()
                self.logger.info(
                    f"Release sync complete (synced={result.synced}, "
                    f"failed={result.failed}, not_found={result.not_found}, "
                    f"requests_updated={result.requests_updated})"
                )
            except Exception as exc:
                self.logger.exception(f"Release sync failed: {exc}")
            await self._sleep(RELEASE_SYNC_INTERVAL)

    async def _run_export_loop(self) -> None:
        while not self._shutdown:
            try:
                use_case = self.container.use_cases.releases.export_finished
                result = await use_case.execute()
                if result.succeeded or result.failed:
                    self.logger.info(
                        f"Export finished series complete "
                        f"(succeeded={result.succeeded}, failed={result.failed})"
                    )
            except Exception as exc:
                self.logger.exception(f"Export task failed: {exc}")
            await self._sleep(EXPORT_INTERVAL)

    async def _run_regrab_loop(self) -> None:
        while not self._shutdown:
            try:
                use_case = self.container.use_cases.releases.regrab_outdated
                await use_case.execute()
            except Exception as exc:
                self.logger.exception(f"Regrab task failed: {exc}")
            await self._sleep(REGRAB_INTERVAL)

    async def _sleep(self, seconds: float) -> None:
        """Sleep in short slices so shutdown is observed promptly."""

        remaining = seconds
        step = 1.0
        while remaining > 0 and not self._shutdown:
            await asyncio.sleep(min(step, remaining))
            remaining -= step


async def main() -> None:
    """Entry point for the scheduler worker process."""

    service = SchedulerService()
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop_event.set)

    service_task = asyncio.create_task(service.start())
    await stop_event.wait()
    await service.shutdown()
    service_task.cancel()
    try:
        await service_task
    except asyncio.CancelledError:
        pass


if __name__ == "__main__":
    asyncio.run(main())
