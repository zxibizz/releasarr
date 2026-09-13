"""Async SQLAlchemy engine and session factories."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from functools import lru_cache

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.settings.config import AppSettings, get_settings


@lru_cache(maxsize=1)
def get_async_engine(settings: AppSettings | None = None) -> AsyncEngine:
    """Create (or retrieve) the global async SQLAlchemy engine."""

    settings = settings or get_settings()
    return create_async_engine(settings.database_url, echo=False, pool_pre_ping=True)


@lru_cache(maxsize=1)
def get_sessionmaker(settings: AppSettings | None = None) -> async_sessionmaker[AsyncSession]:
    """Return a cached async session factory."""

    engine = get_async_engine(settings=settings)
    return async_sessionmaker(engine, expire_on_commit=False)


class DBManager:
    """Utility wrapper exposing transactional access to the database."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._session_factory = session_factory

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        """Yield a raw session without an implicit transaction."""

        async with self._session_factory() as db_session:
            yield db_session

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[AsyncSession]:
        """Yield a session wrapped in a transaction scope."""

        async with self._session_factory() as db_session:
            async with db_session.begin():
                yield db_session


@lru_cache(maxsize=1)
def get_db_manager(settings: AppSettings | None = None) -> DBManager:
    """Provide a singleton DB manager tied to the configured sessionmaker."""

    session_factory = get_sessionmaker(settings=settings)
    return DBManager(session_factory)


__all__ = ["DBManager", "get_async_engine", "get_db_manager", "get_sessionmaker"]
