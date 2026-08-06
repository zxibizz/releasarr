"""Background scheduler service for running sync tasks."""

import asyncio
import signal
from types import FrameType

from loguru import logger

from src.core.container import get_container
from src.tasks.sync_releases import SyncReleasesTask
from src.infrastructure.qbittorrent import QbittorrentClient


class SchedulerService:
    """Service that runs background sync tasks periodically."""

    def __init__(self) -> None:
        self._shutdown = False
        self.container = get_container()
        self.logger = logger.bind(service="Scheduler")

    async def start(self) -> None:
        """Start the scheduler service."""
        self.logger.info("Starting scheduler service")
        
        # Determine strictness of QBT configuration
        # If not configured, we just log a warning and skip that task
        # instead of crashing the whole scheduler
        settings = self.container.settings
        self.qbt_configured = bool(
             settings.qbittorrent_url and settings.qbittorrent_username
        )
        if not self.qbt_configured:
            self.logger.warning("QBittorrent not configured. Release sync will be disabled.")

        tasks = [
            asyncio.create_task(self._run_sonarr_sync_loop()),
            asyncio.create_task(self._run_release_sync_loop()),
        ]

        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            self.logger.info("Scheduler tasks cancelled")
        finally:
            await self.shutdown()

    async def shutdown(self) -> None:
        """Gracefully shutdown the service."""
        self.logger.info("Shutting down scheduler service")
        self._shutdown = True
        await self.container.shutdown()

    async def _run_sonarr_sync_loop(self) -> None:
        """Run Sonarr sync every 60 minutes."""
        while not self._shutdown:
            try:
                self.logger.info("Starting Sonarr sync")
                # Initialize resources for this run if needed, 
                # but container is singleton so we just use it.
                # However, we must ensure startup() is called at least once.
                # It's idempotent so calling it again is fine or check updated status.
                # The container.startup() is usually lightweight.
                self.container.startup()
                
                use_case = self.container.use_cases.media_requests.sync_sonarr
                result = await use_case.execute()
                
                self.logger.info(
                    "Sonarr sync complete "
                    f"(created={result.created}, updated={result.updated}, completed={result.completed})"
                )
            except Exception as exc:
                self.logger.exception(f"Sonarr sync failed: {exc}")

            # Sleep for 60 minutes
            await self._sleep(60 * 60)

    async def _run_release_sync_loop(self) -> None:
        """Run Release sync every 30 seconds."""
        if not self.qbt_configured:
            return

        while not self._shutdown:
            try:
                self.container.startup()
                settings = self.container.settings
                
                # Re-check settings if dynamic config implementation changes, 
                # but for now settings are env vars loaded at start.

                client = QbittorrentClient(
                    base_url=settings.qbittorrent_url,
                    username=settings.qbittorrent_username,
                    password=settings.qbittorrent_password,
                    timeout=settings.qbittorrent_timeout,
                )
                
                # Note: QbittorrentClient doesn't have an explicit startup/connect method 
                # that persists, it uses httpx.AsyncClient nicely.
                # However, ensure we don't leak sessions if client holds one.
                # The SyncReleasesTask takes a client instance.
                
                task = SyncReleasesTask(
                    db=self.container.db_manager,
                    client=client,
                    category=settings.qbittorrent_category,
                )
                
                result = await task.execute()
                
                # Explicitly close the client used for this task run
                await client.close()

                self.logger.info(
                    f"Release sync complete (synced={result.synced}, failed={result.failed}, not_found={result.not_found})"
                )
            except Exception as exc:
                self.logger.exception(f"Release sync failed: {exc}")

            # Sleep for 30 seconds
            await self._sleep(30)

    async def _sleep(self, seconds: float) -> None:
        """Sleep that can be interrupted by shutdown."""
        if self._shutdown:
            return
        
        # Check shutdown status periodically or sleep
        # For simplicity in this loop, simple sleep is fine as 
        # asyncio.CancelledError from main gather will interrupt it.
        await asyncio.sleep(seconds)


async def main() -> None:
    """Entry point for the scheduler service."""
    service = SchedulerService()
    
    # Handle signals
    loop = asyncio.get_running_loop()
    
    stop_event = asyncio.Event()

    def handle_signal():
        stop_event.set()

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, handle_signal)

    service_task = asyncio.create_task(service.start())

    await stop_event.wait()
    
    # Signal shutdown
    await service.shutdown()
    service_task.cancel()
    try:
        await service_task
    except asyncio.CancelledError:
        pass


if __name__ == "__main__":
    asyncio.run(main())
