"""Data transfer objects returned by task use cases."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from src.domain.enums import SyncJobKind, SyncJobStatus


@dataclass(slots=True)
class ScheduledTaskDTO:
    """A recurring task together with its computed next run time."""

    kind: SyncJobKind
    interval_seconds: int
    last_execution: datetime | None
    last_duration_ms: int | None
    last_status: SyncJobStatus | None
    last_error: str | None
    next_execution: datetime | None


__all__ = ["ScheduledTaskDTO"]
