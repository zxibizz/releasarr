"""Tests for the SQLAlchemy-backed refresh token and service key repositories."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from src.db.session import DBManager
from src.domain import models
from src.domain.enums import UserRole
from src.infrastructure.auth import (
    SqlAlchemyRefreshTokenRepository,
    SqlAlchemyServiceApiKeyRepository,
)


@pytest.fixture()
async def user_id(db_manager: DBManager) -> str:
    async with db_manager.transaction() as session:
        session.add(
            models.User(
                id="user-1",
                username="carol",
                password_hash="unused",
                role=UserRole.USER,
            )
        )
    return "user-1"


@pytest.fixture()
def repository(db_manager: DBManager) -> SqlAlchemyRefreshTokenRepository:
    return SqlAlchemyRefreshTokenRepository(db=db_manager)


@pytest.fixture()
def service_keys(db_manager: DBManager) -> SqlAlchemyServiceApiKeyRepository:
    return SqlAlchemyServiceApiKeyRepository(db=db_manager)


async def test_stored_window_comes_back_timezone_aware(
    repository: SqlAlchemyRefreshTokenRepository, user_id: str
) -> None:
    issued_at = datetime.now(UTC)
    expires_at = issued_at + timedelta(days=1)
    await repository.store(
        id="token-1",
        user_id=user_id,
        family_id="family-1",
        token_hash="hash-1",
        remember=False,
        issued_at=issued_at,
        expires_at=expires_at,
    )

    record = await repository.get_by_hash("hash-1")

    assert record is not None
    # Refreshing compares this to ``datetime.now(UTC)``, which SQLite cannot do
    # with the naive value it stores in a ``DateTime(timezone=True)`` column.
    assert record.expires_at == expires_at
    assert record.issued_at == issued_at


async def test_revocation_timestamp_comes_back_timezone_aware(
    repository: SqlAlchemyRefreshTokenRepository, user_id: str
) -> None:
    await repository.store(
        id="token-1",
        user_id=user_id,
        family_id="family-1",
        token_hash="hash-1",
        remember=False,
        issued_at=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )

    await repository.revoke("token-1")

    record = await repository.get_by_hash("hash-1")
    assert record is not None
    assert record.revoked_at is not None
    assert record.revoked_at <= datetime.now(UTC)


async def test_service_key_created_at_comes_back_timezone_aware(
    service_keys: SqlAlchemyServiceApiKeyRepository,
) -> None:
    await service_keys.replace(id="key-1", key="the-key")

    record = await service_keys.get()

    assert record is not None
    assert record.created_at <= datetime.now(UTC)
