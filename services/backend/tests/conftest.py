"""Shared pytest fixtures for backend tests."""

from __future__ import annotations

import os

# Must be set before anything imports src.settings.config, since AppSettings is
# read once and cached; a blank secret would otherwise fail container startup.
os.environ.setdefault("RELEASARR_AUTH_SECRET", "test-secret")

from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from loguru import logger
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.api.app import app
from src.api.dependencies.auth import get_principal
from src.application.interfaces.users import UserRecord
from src.application.use_cases.auth import Principal
from src.db import Base
from src.db.session import DBManager
from src.domain import models  # noqa: F401  (ensures models register on the metadata)
from src.domain.enums import UserRole

# Every route used to accept any request carrying the single global API key.
# Standing in for that here keeps every existing test authenticated as an
# unrestricted admin by default; tests exercising auth itself remove the
# override for the one call they care about.
TEST_ADMIN_USER = UserRecord(
    id="test-admin",
    username="admin",
    display_name="Test Admin",
    password_hash="unused",
    role=UserRole.ADMIN,
    is_active=True,
    can_view_all_requests=True,
    can_access_tasks=True,
    can_access_indexers=True,
    can_access_logs=True,
    allowed_root_folders=[],
    failed_login_attempts=0,
    locked_until=None,
    last_login_at=None,
    created_at=datetime.now(UTC),
    updated_at=datetime.now(UTC),
)
TEST_ADMIN_PRINCIPAL = Principal(user=TEST_ADMIN_USER, via="session")


@pytest.fixture(autouse=True)
def _default_authenticated_principal() -> Iterator[None]:
    app.dependency_overrides[get_principal] = lambda: TEST_ADMIN_PRINCIPAL
    try:
        yield
    finally:
        app.dependency_overrides.pop(get_principal, None)


@pytest.fixture()
async def api_client() -> AsyncIterator[AsyncClient]:
    """Async HTTP client bound to the FastAPI app."""

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


@pytest.fixture()
async def db_engine() -> AsyncIterator[AsyncEngine]:
    """In-memory SQLite engine with the domain schema applied."""

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest.fixture()
async def session_factory(
    db_engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    """Async session factory bound to the in-memory engine."""

    return async_sessionmaker(db_engine, expire_on_commit=False)


@pytest.fixture()
async def db_manager(session_factory: async_sessionmaker[AsyncSession]) -> DBManager:
    """Convenience wrapper mirroring production DB manager behaviour."""

    return DBManager(session_factory)


@pytest.fixture()
def captured_records() -> Iterator[list[dict[str, Any]]]:
    """Collect the ``extra`` payload Loguru would serialise to the log file.

    The sink is added at INFO because that is the floor the log file records at,
    so anything this fixture misses would be missing from a request's activity
    view as well.
    """

    records: list[dict[str, Any]] = []
    sink_id = logger.add(
        lambda message: records.append(
            {
                "message": message.record["message"],
                "level": message.record["level"].name,
                **message.record["extra"],
            }
        ),
        level="INFO",
    )
    try:
        yield records
    finally:
        logger.remove(sink_id)
