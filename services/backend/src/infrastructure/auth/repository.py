"""SQLAlchemy-backed refresh token and service API key repositories."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import delete, select

from src.application.interfaces.auth import (
    RefreshTokenRecord,
    RefreshTokenRepository,
    ServiceApiKeyRecord,
    ServiceApiKeyRepository,
)
from src.db.repository import BaseSqlAlchemyRepository
from src.domain import models


@dataclass(slots=True)
class SqlAlchemyRefreshTokenRepository(BaseSqlAlchemyRepository, RefreshTokenRepository):
    """Persist refresh tokens using SQLAlchemy sessions."""

    async def store(
        self,
        *,
        id: str,
        user_id: str,
        family_id: str,
        token_hash: str,
        remember: bool,
        issued_at: datetime,
        expires_at: datetime,
    ) -> RefreshTokenRecord:
        async with self.db.transaction() as session:
            token = models.RefreshToken(
                id=id,
                user_id=user_id,
                family_id=family_id,
                token_hash=token_hash,
                remember=remember,
                issued_at=issued_at,
                expires_at=expires_at,
            )
            session.add(token)
            await session.flush()
            await session.refresh(token)
            return self._to_record(token)

    async def get_by_hash(self, token_hash: str) -> RefreshTokenRecord | None:
        async with self.db.session() as session:
            stmt = select(models.RefreshToken).where(models.RefreshToken.token_hash == token_hash)
            result = await session.execute(stmt)
            token = result.scalar_one_or_none()
            return self._to_record(token) if token is not None else None

    async def revoke(self, token_id: str) -> None:
        async with self.db.transaction() as session:
            token = await session.get(models.RefreshToken, token_id)
            if token is not None and token.revoked_at is None:
                token.revoked_at = models.utc_now()

    async def revoke_family(self, family_id: str) -> None:
        async with self.db.transaction() as session:
            stmt = select(models.RefreshToken).where(
                models.RefreshToken.family_id == family_id,
                models.RefreshToken.revoked_at.is_(None),
            )
            result = await session.execute(stmt)
            now = models.utc_now()
            for token in result.scalars().all():
                token.revoked_at = now

    async def purge_expired(self, *, now: datetime) -> int:
        async with self.db.transaction() as session:
            result = await session.execute(
                delete(models.RefreshToken).where(models.RefreshToken.expires_at < now)
            )
            return result.rowcount or 0

    @staticmethod
    def _to_record(token: models.RefreshToken) -> RefreshTokenRecord:
        return RefreshTokenRecord(
            id=token.id,
            user_id=token.user_id,
            family_id=token.family_id,
            token_hash=token.token_hash,
            remember=token.remember,
            issued_at=token.issued_at,
            expires_at=token.expires_at,
            revoked_at=token.revoked_at,
        )


@dataclass(slots=True)
class SqlAlchemyServiceApiKeyRepository(BaseSqlAlchemyRepository, ServiceApiKeyRepository):
    """Persist the singleton service API key using SQLAlchemy sessions."""

    async def get(self) -> ServiceApiKeyRecord | None:
        async with self.db.session() as session:
            stmt = select(models.ServiceApiKey).limit(1)
            result = await session.execute(stmt)
            key = result.scalar_one_or_none()
            return self._to_record(key) if key is not None else None

    async def get_by_key(self, key: str) -> ServiceApiKeyRecord | None:
        async with self.db.session() as session:
            stmt = select(models.ServiceApiKey).where(models.ServiceApiKey.key == key)
            result = await session.execute(stmt)
            record = result.scalar_one_or_none()
            return self._to_record(record) if record is not None else None

    async def replace(self, *, id: str, key: str) -> ServiceApiKeyRecord:
        async with self.db.transaction() as session:
            await session.execute(delete(models.ServiceApiKey))
            record = models.ServiceApiKey(id=id, key=key)
            session.add(record)
            await session.flush()
            await session.refresh(record)
            return self._to_record(record)

    async def touch_last_used(self, key_id: str, *, at: datetime) -> None:
        async with self.db.transaction() as session:
            key = await session.get(models.ServiceApiKey, key_id)
            if key is not None:
                key.last_used_at = at

    @staticmethod
    def _to_record(key: models.ServiceApiKey) -> ServiceApiKeyRecord:
        return ServiceApiKeyRecord(
            id=key.id,
            key=key.key,
            last_used_at=key.last_used_at,
            created_at=key.created_at,
        )


__all__ = ["SqlAlchemyRefreshTokenRepository", "SqlAlchemyServiceApiKeyRepository"]
