"""Change a scheduled task's interval."""

from __future__ import annotations

from src.application.interfaces.sync_jobs import ScheduledTaskRepository
from src.application.use_cases.tasks.exceptions import SyncJobNotFoundError
from src.domain.enums import SyncJobKind

MIN_INTERVAL_SECONDS = 5


class UpdateTaskIntervalUseCase:
    def __init__(self, repository: ScheduledTaskRepository) -> None:
        self._repository = repository

    async def execute(self, kind: SyncJobKind, interval_seconds: int) -> None:
        if interval_seconds < MIN_INTERVAL_SECONDS:
            raise ValueError(f"interval must be at least {MIN_INTERVAL_SECONDS} seconds")

        # The row is created by the scheduler at boot, so its absence means the
        # kind is unknown rather than merely unscheduled.
        record = await self._repository.get(kind)
        if record is None:
            raise SyncJobNotFoundError(kind.value)

        await self._repository.set_interval(kind, interval_seconds=interval_seconds)


__all__ = ["UpdateTaskIntervalUseCase"]
