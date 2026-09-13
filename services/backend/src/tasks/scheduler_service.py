"""Standalone background worker that runs periodic and on-demand tasks.

This is intentionally a separate process entrypoint (run via
``python -m src.tasks.scheduler_service``) and is never started inside the
FastAPI app, honouring the "no implicit background schedulers in the web app"
architecture principle. It reuses the shared application container so it picks
up the same settings, logging, and clients as the API.

Each task keeps its own loop, driven by the last execution time recorded in the
database so schedules survive a restart. A separate loop drains the jobs the API
queues for manual runs and download-client hooks.
"""

from __future__ import annotations

import asyncio
import signal
import time
from datetime import UTC, datetime

from loguru import logger

from src.application.use_cases.tasks.definitions import DEFAULT_INTERVALS, TASK_ORDER
from src.core.container import AppContainer, get_container
from src.domain.enums import SyncJobKind, SyncJobStatus
from src.tasks.sync_jobs import SyncJobRunner
from src.tasks.sync_steps import SyncSteps

JOB_POLL_INTERVAL = 5
# Upper bound on retained job history, trimmed after each drained job.
JOB_HISTORY_LIMIT = 200


class SchedulerService:
    """Runs the periodic tasks and the on-demand job queue until shutdown."""

    def __init__(self, container: AppContainer | None = None) -> None:
        self._shutdown = False
        self.container = container or get_container()
        self.container.startup()
        self.logger = logger.bind(service="Scheduler")
        self.steps = SyncSteps(container=self.container)

    async def start(self) -> None:
        self.logger.info("Starting scheduler service")
        await self._register_tasks()
        await self._reclaim_interrupted_jobs()

        tasks = [asyncio.create_task(self._run_scheduled_loop(kind)) for kind in TASK_ORDER]
        tasks.append(asyncio.create_task(self._run_job_queue_loop()))

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

    async def _register_tasks(self) -> None:
        """Make every known task visible to the API, even before its first run."""

        repository = self.container.repositories.scheduled_tasks
        for kind, interval in DEFAULT_INTERVALS.items():
            try:
                await repository.register(kind=kind, interval_seconds=interval)
            except Exception as exc:
                self.logger.exception(f"Failed to register task {kind.value}: {exc}")

    async def _reclaim_interrupted_jobs(self) -> None:
        """Fail jobs a previous process left running.

        This process is the only consumer of the queue, so anything still
        marked running at startup died with its worker.
        """

        try:
            stale = await self.container.repositories.sync_jobs.fail_running(
                error="Scheduler restarted before the job finished"
            )
        except Exception as exc:
            self.logger.exception(f"Failed to reclaim interrupted jobs: {exc}")
            return

        if stale:
            self.logger.warning(f"Failed {stale} job(s) interrupted by a restart")

    async def _run_scheduled_loop(self, kind: SyncJobKind) -> None:
        interval = DEFAULT_INTERVALS[kind]

        while not self._shutdown:
            try:
                delay = await self._seconds_until_due(kind, interval)
            except Exception as exc:
                self.logger.bind(task=kind.value).exception(
                    f"Failed to read schedule for {kind.value}: {exc}"
                )
                delay = interval

            if delay > 0:
                await self._sleep(delay)
                continue

            await self._run_scheduled(kind)

    async def _seconds_until_due(self, kind: SyncJobKind, interval: int) -> float:
        """Seconds remaining before ``kind`` is due, or 0 when it should run now."""

        record = await self.container.repositories.scheduled_tasks.get(kind)
        last_execution = record.last_execution if record else None
        if last_execution is None:
            return 0.0

        if last_execution.tzinfo is None:
            last_execution = last_execution.replace(tzinfo=UTC)

        elapsed = (datetime.now(UTC) - last_execution).total_seconds()
        return max(0.0, interval - elapsed)

    async def _run_scheduled(self, kind: SyncJobKind) -> None:
        """Run one task on its schedule and record the outcome."""

        # Scheduled runs leave no job history, so these lines are all the logs
        # view has to show for them. Tagging them keeps the task filter honest.
        task_logger = self.logger.bind(task=kind.value)

        started = time.monotonic()
        status = SyncJobStatus.COMPLETED
        error: str | None = None
        summary: dict[str, object] = {}

        try:
            summary = await self.steps.for_kind(kind)()
        except Exception as exc:
            status = SyncJobStatus.FAILED
            error = str(exc)
            task_logger.exception(f"Task {kind.value} failed: {exc}")

        duration_ms = int((time.monotonic() - started) * 1000)

        if status is SyncJobStatus.COMPLETED:
            task_logger.info(f"Task {kind.value} complete ({duration_ms}ms): {summary}")

        try:
            await self.container.repositories.scheduled_tasks.record_run(
                kind,
                status=status,
                duration_ms=duration_ms,
                error=error,
            )
        except Exception as exc:
            task_logger.exception(f"Failed to record run of {kind.value}: {exc}")
            # Without a recorded execution the loop would spin, so back off.
            await self._sleep(DEFAULT_INTERVALS[kind])

    async def _run_job_queue_loop(self) -> None:
        """Drain jobs queued over the API."""

        runner = SyncJobRunner(
            repository=self.container.repositories.sync_jobs,
            steps=self.steps,
            logger=self.logger,
        )

        while not self._shutdown:
            try:
                # Keep draining while work remains so a burst of queued jobs is
                # not spread across poll intervals.
                drained = False
                while not self._shutdown and await runner.run_next() is not None:
                    drained = True

                if drained:
                    await self.container.repositories.sync_jobs.prune(keep=JOB_HISTORY_LIMIT)
            except Exception as exc:
                self.logger.exception(f"Job queue failed: {exc}")
            await self._sleep(JOB_POLL_INTERVAL)

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
