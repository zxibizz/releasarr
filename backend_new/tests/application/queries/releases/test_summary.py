"""Tests for the release summary query helper."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from src.application.queries.releases import ReleaseSummaryQuery
from src.db.session import DBManager
from src.domain import models
from src.domain.enums import ReleaseStatus


@pytest.fixture()
async def engine() -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)  # type: ignore[arg-type]
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest.fixture()
async def session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest.fixture()
async def db_manager(session_factory: async_sessionmaker[AsyncSession]) -> DBManager:
    return DBManager(session_factory)


@pytest.mark.asyncio
async def test_release_summary_counts_statuses(db_manager: DBManager) -> None:
    query = ReleaseSummaryQuery(db=db_manager)

    async with db_manager.transaction() as session:
        session.add_all(
            [
                models.Release(
                    id=f"rel-pending-{index}",
                    name=f"Pending {index}",
                    info_hash=f"HASH-P-{index}",
                    size_bytes=0,
                    status=ReleaseStatus.PENDING,
                    progress=0.0,
                    download_speed=0.0,
                    upload_speed=0.0,
                    seeders=0,
                    leechers=0,
                    ratio=0.0,
                )
                for index in range(2)
            ]
        )
        session.add(
            models.Release(
                id="rel-complete",
                name="Complete",
                info_hash="HASH-C-1",
                size_bytes=0,
                status=ReleaseStatus.COMPLETED,
                progress=1.0,
                download_speed=0.0,
                upload_speed=0.0,
                seeders=0,
                leechers=0,
                ratio=1.0,
            )
        )

    summary = await query.fetch()

    assert summary.total == 3
    assert summary.count(ReleaseStatus.PENDING) == 2
    assert summary.count(ReleaseStatus.COMPLETED) == 1
    # Missing statuses should default to zero
    assert summary.count(ReleaseStatus.DOWNLOADING) == 0


@pytest.mark.asyncio
async def test_release_summary_handles_empty_db(db_manager: DBManager) -> None:
    query = ReleaseSummaryQuery(db=db_manager)

    summary = await query.fetch()

    assert summary.total == 0
    for status in ReleaseStatus:
        assert summary.count(status) == 0
