"""Queue task runs for the scheduler worker to pick up."""

from __future__ import annotations

from collections.abc import Sequence

from loguru._logger import Logger

from src.application.interfaces.sync_jobs import EnqueueSyncJobResult, SyncJobRepository
from src.core.logging import get_logger
from src.domain.enums import SyncJobKind, SyncJobTrigger


class EnqueueSyncJobUseCase:
    """Use case recording a request for the scheduler to run tasks."""

    def __init__(
        self,
        repository: SyncJobRepository,
        logger: Logger | None = None,
    ) -> None:
        self._repository = repository
        self._logger = logger or get_logger(component="enqueue_sync_job")

    async def execute(
        self,
        *,
        kinds: Sequence[SyncJobKind],
        trigger: SyncJobTrigger = SyncJobTrigger.API,
    ) -> list[EnqueueSyncJobResult]:
        if not kinds:
            raise ValueError("At least one task kind is required")

        results = await self._repository.enqueue_sequence(kinds=kinds, trigger=trigger)

        created = [result.job.kind.value for result in results if result.created]
        reused = [result.job.kind.value for result in results if not result.created]

        if created:
            self._logger.info(
                "Queued tasks",
                tasks=created,
                trigger=trigger.value,
            )
        if reused:
            self._logger.debug(
                "Tasks already queued; reusing them",
                tasks=reused,
                trigger=trigger.value,
            )

        return results


__all__ = ["EnqueueSyncJobUseCase"]
