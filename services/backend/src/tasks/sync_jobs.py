"""Execution of task runs queued by the API.

The API and the scheduler are separate processes, so a manual run (or a download
client reporting a finished torrent) is recorded as a row in ``sync_jobs`` and
picked up here.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from loguru._logger import Logger

from src.application.interfaces.sync_jobs import SyncJobRecord, SyncJobRepository
from src.core.logging import get_logger
from src.domain.enums import SyncJobStatus
from src.tasks.sync_steps import SyncSteps


@dataclass(slots=True)
class SyncJobRunner:
    """Claims queued jobs and runs the task each one names."""

    repository: SyncJobRepository
    steps: SyncSteps
    logger: Logger = field(default_factory=lambda: get_logger(component="sync_job_runner"))

    async def run_next(self) -> SyncJobRecord | None:
        """Run the oldest queued job, or return None when the queue is empty."""

        job = await self.repository.claim_next()
        if job is None:
            return None

        self.logger.info(
            "Running task",
            job_id=job.id,
            task=job.kind.value,
            trigger=job.trigger.value,
        )

        try:
            summary = await self.steps.for_kind(job.kind)()
        except Exception as exc:
            self.logger.exception(
                "Task failed",
                job_id=job.id,
                task=job.kind.value,
                error=str(exc),
            )
            await self.repository.finish(
                job.id,
                status=SyncJobStatus.FAILED,
                result={"error": str(exc)},
                error=str(exc),
            )
            return job

        await self.repository.finish(
            job.id,
            status=SyncJobStatus.COMPLETED,
            result=summary,
        )
        self.logger.info("Task complete", job_id=job.id, task=job.kind.value)
        return job


__all__ = ["SyncJobRunner"]
