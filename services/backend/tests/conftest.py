"""Shared pytest fixtures for backend tests."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
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
from src.db import Base
from src.db.session import DBManager
from src.domain import models  # noqa: F401  (ensures models register on the metadata)


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
