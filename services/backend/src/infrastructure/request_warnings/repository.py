"""SQLAlchemy-backed implementation of the request warning repository protocol."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from uuid import uuid4

from sqlalchemy import delete, select

from src.application.interfaces.request_warnings import (
    RequestWarningRecord,
    RequestWarningRepository,
)
from src.db.repository import BaseSqlAlchemyRepository
from src.domain import models
from src.domain.enums import RequestWarningCode


@dataclass(slots=True)
class SqlAlchemyRequestWarningRepository(BaseSqlAlchemyRepository, RequestWarningRepository):
    """Persist request warnings using SQLAlchemy sessions.

    Every write here is a plain SQL delete-then-insert rather than an ORM
    relationship: `RequestWarning` has no relationship back to `MediaRequest`
    or `Release` (see the model's docstring), so this repository owns clearing
    a warning's rows explicitly instead of leaning on cascades that, for this
    table, would not fire on every removal path anyway.
    """

    async def replace_for_requests(
        self,
        code: RequestWarningCode,
        request_ids: Sequence[str],
        warnings: Sequence[RequestWarningRecord],
    ) -> None:
        if not request_ids:
            return
        async with self.db.transaction() as session:
            await session.execute(
                delete(models.RequestWarning).where(
                    models.RequestWarning.code == code,
                    models.RequestWarning.request_id.in_(request_ids),
                )
            )
            for warning in warnings:
                session.add(self._to_model(warning))

    async def replace_for_releases(
        self,
        code: RequestWarningCode,
        release_ids: Sequence[str],
        warnings: Sequence[RequestWarningRecord],
    ) -> None:
        if not release_ids:
            return
        async with self.db.transaction() as session:
            await session.execute(
                delete(models.RequestWarning).where(
                    models.RequestWarning.code == code,
                    models.RequestWarning.release_id.in_(release_ids),
                )
            )
            for warning in warnings:
                session.add(self._to_model(warning))

    async def delete_for_release(self, release_id: str) -> None:
        async with self.db.transaction() as session:
            await session.execute(
                delete(models.RequestWarning).where(models.RequestWarning.release_id == release_id)
            )

    async def delete_for_request_release(self, request_id: str, release_id: str) -> None:
        async with self.db.transaction() as session:
            await session.execute(
                delete(models.RequestWarning).where(
                    models.RequestWarning.request_id == request_id,
                    models.RequestWarning.release_id == release_id,
                )
            )

    async def list_for_requests(
        self, request_ids: Sequence[str]
    ) -> dict[str, list[RequestWarningRecord]]:
        if not request_ids:
            return {}
        async with self.db.session() as session:
            stmt = select(models.RequestWarning).where(
                models.RequestWarning.request_id.in_(request_ids)
            )
            result = await session.execute(stmt)
            return self._group_by(result.scalars().all(), key="request_id")

    async def list_for_releases(
        self, release_ids: Sequence[str]
    ) -> dict[str, list[RequestWarningRecord]]:
        if not release_ids:
            return {}
        async with self.db.session() as session:
            stmt = select(models.RequestWarning).where(
                models.RequestWarning.release_id.in_(release_ids)
            )
            result = await session.execute(stmt)
            return self._group_by(result.scalars().all(), key="release_id")

    @staticmethod
    def _to_model(warning: RequestWarningRecord) -> models.RequestWarning:
        return models.RequestWarning(
            id=str(uuid4()),
            request_id=warning.request_id,
            release_id=warning.release_id,
            code=warning.code,
            details=warning.details,
        )

    @staticmethod
    def _to_record(row: models.RequestWarning) -> RequestWarningRecord:
        return RequestWarningRecord(
            request_id=row.request_id,
            release_id=row.release_id,
            code=row.code,
            details=row.details,
            created_at=row.created_at,
        )

    @classmethod
    def _group_by(
        cls,
        rows: Sequence[models.RequestWarning],
        *,
        key: str,
    ) -> dict[str, list[RequestWarningRecord]]:
        grouped: dict[str, list[RequestWarningRecord]] = defaultdict(list)
        for row in rows:
            grouped_key = getattr(row, key)
            if grouped_key is None:
                continue
            grouped[grouped_key].append(cls._to_record(row))
        return dict(grouped)


__all__ = ["SqlAlchemyRequestWarningRepository"]
