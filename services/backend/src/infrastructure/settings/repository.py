"""SQLAlchemy-backed persistence for the runtime settings override row."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import delete, select

from src.application.interfaces.settings import AppSettingsRecord, AppSettingsRepository
from src.db.repository import BaseSqlAlchemyRepository
from src.domain import models

_SETTINGS_ID = "app_settings"


@dataclass(slots=True)
class SqlAlchemyAppSettingsRepository(BaseSqlAlchemyRepository, AppSettingsRepository):
    """Persist the singleton settings override row."""

    async def get(self) -> AppSettingsRecord | None:
        async with self.db.session() as session:
            result = await session.execute(select(models.AppSettings).limit(1))
            row = result.scalar_one_or_none()
            return self._to_record(row) if row is not None else None

    async def save_overrides(self, *, overrides: dict[str, Any]) -> AppSettingsRecord:
        async with self.db.transaction() as session:
            result = await session.execute(select(models.AppSettings).limit(1))
            row = result.scalar_one_or_none()
            if row is None:
                row = models.AppSettings(id=_SETTINGS_ID, overrides=dict(overrides), revision=1)
                session.add(row)
            else:
                row.overrides = dict(overrides)
                row.revision = int(row.revision) + 1
            await session.flush()
            await session.refresh(row)
            return self._to_record(row)

    async def get_revision(self) -> int:
        async with self.db.session() as session:
            result = await session.execute(select(models.AppSettings.revision).limit(1))
            revision = result.scalar_one_or_none()
            return int(revision) if revision is not None else 0

    async def delete(self) -> None:
        async with self.db.transaction() as session:
            await session.execute(delete(models.AppSettings))

    @staticmethod
    def _to_record(row: models.AppSettings) -> AppSettingsRecord:
        return AppSettingsRecord(
            id=row.id,
            overrides=dict(row.overrides or {}),
            revision=int(row.revision),
        )


__all__ = ["SqlAlchemyAppSettingsRepository"]
