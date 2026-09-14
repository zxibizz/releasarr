"""Tests for the SQLAlchemy-backed user repository."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from src.application.interfaces.users import CreateUserData, UpdateUserData
from src.db.session import DBManager
from src.infrastructure.users.repository import SqlAlchemyUserRepository


@pytest.fixture()
def repository(db_manager: DBManager) -> SqlAlchemyUserRepository:
    return SqlAlchemyUserRepository(db=db_manager)


async def test_locked_until_comes_back_timezone_aware(
    repository: SqlAlchemyUserRepository,
) -> None:
    user = await repository.create_user(
        CreateUserData(id="user-1", username="carol", password_hash="unused")
    )
    locked_until = datetime.now(UTC) + timedelta(minutes=15)
    await repository.update_user(user.id, UpdateUserData(locked_until=locked_until))

    stored = await repository.get_by_username("carol")

    assert stored is not None
    # Logging in compares this to ``datetime.now(UTC)`` to decide whether the
    # lockout is still in force.
    assert stored.locked_until == locked_until
    assert stored.created_at <= datetime.now(UTC)
