"""Optimized read-model helpers for release aggregate data."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from src.application.interfaces.releases import ReleaseRepository
from src.domain.enums import ReleaseStatus


@dataclass(slots=True, frozen=True)
class ReleaseSummary:
    """Aggregated release statistics."""

    total: int
    by_status: Mapping[ReleaseStatus, int]

    def count(self, status: ReleaseStatus) -> int:
        """Return the count for a specific status."""

        return int(self.by_status.get(status, 0))


class ReleaseSummaryQuery:
    """Query helper returning aggregated release stats."""

    def __init__(self, repository: ReleaseRepository) -> None:
        self._repository = repository

    async def fetch(self) -> ReleaseSummary:
        counts = await self._repository.count_by_status()

        total = sum(counts.values())
        # Ensure all statuses are represented even if absent in the DB.
        normalized: dict[ReleaseStatus, int] = {status: 0 for status in ReleaseStatus}
        normalized.update(counts)
        return ReleaseSummary(total=total, by_status=normalized)


__all__ = ["ReleaseSummary", "ReleaseSummaryQuery"]
