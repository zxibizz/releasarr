"""Shared SQLAlchemy repository foundation.

Centralises the pieces every repository needs: a handle to the
:class:`~src.db.session.DBManager`, a filtered ``COUNT`` helper, and consistent
offset/limit pagination so individual repositories stay focused on their own
mapping logic.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy import ColumnElement, Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import DBManager

Filter = ColumnElement[bool]


@dataclass(slots=True)
class BaseSqlAlchemyRepository:
    """Common behaviour shared by SQLAlchemy-backed repositories."""

    db: DBManager

    async def _count(
        self,
        session: AsyncSession,
        count_column: Any,
        filters: Sequence[Filter],
    ) -> int:
        stmt = select(func.count(count_column)).where(*filters)
        result = await session.execute(stmt)
        return int(result.scalar() or 0)

    @staticmethod
    def _paginate[T: tuple[Any, ...]](stmt: Select[T], *, page: int, per_page: int) -> Select[T]:
        return stmt.offset((page - 1) * per_page).limit(per_page)


__all__ = ["BaseSqlAlchemyRepository", "Filter"]
