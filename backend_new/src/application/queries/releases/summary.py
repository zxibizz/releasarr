"""Optimized read-model helpers for release aggregate data."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import DBManager
from src.domain import models
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

    def __init__(self, db: DBManager) -> None:
        self._db = db

    async def fetch(self) -> ReleaseSummary:
        async with self._db.session() as session:
            counts = await self._load_counts(session)

        total = sum(counts.values())
        # Ensure all statuses are represented even if absent in the DB.
        normalized: dict[ReleaseStatus, int] = {status: 0 for status in ReleaseStatus}
        normalized.update(counts)
        return ReleaseSummary(total=total, by_status=normalized)

    async def _load_counts(self, session: AsyncSession) -> dict[ReleaseStatus, int]:
        stmt: Select[tuple[ReleaseStatus, int]] = select(
            models.Release.status, func.count(models.Release.id)
        ).group_by(models.Release.status)
        result = await session.execute(stmt)
        rows = result.all()
        return {status: int(count) for status, count in rows}


__all__ = ["ReleaseSummary", "ReleaseSummaryQuery"]
