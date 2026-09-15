"""Tests for the SQLAlchemy-backed request warning repository.

The scenarios worth pinning down explicitly are the two the FK cascade does
not cover: deleting a release (SQLite does not enforce `ondelete`) and
unlinking a release shared between requests (no FK is violated at all).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.application.interfaces.request_warnings import RequestWarningRecord
from src.db import Base
from src.db.session import DBManager
from src.domain import models
from src.domain.enums import MediaRequestStatus, MediaType, RequestWarningCode
from src.infrastructure.request_warnings.repository import SqlAlchemyRequestWarningRepository


@pytest.fixture()
async def engine() -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture()
async def session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest.fixture()
async def db_manager(session_factory: async_sessionmaker[AsyncSession]) -> DBManager:
    return DBManager(session_factory)


@pytest.fixture()
async def repository(db_manager: DBManager) -> SqlAlchemyRequestWarningRepository:
    return SqlAlchemyRequestWarningRepository(db=db_manager)


async def _seed_request(db_manager: DBManager, request_id: str) -> None:
    now = datetime.now(UTC)
    async with db_manager.transaction() as session:
        session.add(
            models.MediaRequest(
                id=request_id,
                media_type=MediaType.MOVIE,
                status=MediaRequestStatus.PENDING,
                title=f"Title {request_id}",
                year=2024,
                genres=[],
                created_at=now,
                updated_at=now,
            )
        )


async def _seed_release(db_manager: DBManager, release_id: str) -> None:
    now = datetime.now(UTC)
    async with db_manager.transaction() as session:
        session.add(
            models.Release(
                id=release_id,
                name=release_id,
                info_hash=f"hash-{release_id}",
                size_bytes=1,
                added_at=now,
            )
        )


@pytest.mark.asyncio
async def test_replace_for_requests_is_a_full_replace(
    repository: SqlAlchemyRequestWarningRepository,
    db_manager: DBManager,
) -> None:
    await _seed_request(db_manager, "req-1")
    await _seed_release(db_manager, "rel-1")
    await _seed_release(db_manager, "rel-2")

    await repository.replace_for_requests(
        RequestWarningCode.MAPPING_OVERLAP,
        ["req-1"],
        [
            RequestWarningRecord(
                request_id="req-1", release_id="rel-1", code=RequestWarningCode.MAPPING_OVERLAP
            )
        ],
    )
    by_request = await repository.list_for_requests(["req-1"])
    assert [w.release_id for w in by_request["req-1"]] == ["rel-1"]

    # A second call with a different release replaces, rather than appends to,
    # the first - and an empty list clears the code entirely.
    await repository.replace_for_requests(
        RequestWarningCode.MAPPING_OVERLAP,
        ["req-1"],
        [
            RequestWarningRecord(
                request_id="req-1", release_id="rel-2", code=RequestWarningCode.MAPPING_OVERLAP
            )
        ],
    )
    by_request = await repository.list_for_requests(["req-1"])
    assert [w.release_id for w in by_request["req-1"]] == ["rel-2"]

    await repository.replace_for_requests(RequestWarningCode.MAPPING_OVERLAP, ["req-1"], [])
    assert await repository.list_for_requests(["req-1"]) == {}


@pytest.mark.asyncio
async def test_replace_for_requests_only_touches_its_own_code(
    repository: SqlAlchemyRequestWarningRepository,
    db_manager: DBManager,
) -> None:
    await _seed_request(db_manager, "req-1")
    await _seed_release(db_manager, "rel-1")

    await repository.replace_for_releases(
        RequestWarningCode.REGRAB_INDEXER_UNAVAILABLE,
        ["rel-1"],
        [
            RequestWarningRecord(
                request_id="req-1",
                release_id="rel-1",
                code=RequestWarningCode.REGRAB_INDEXER_UNAVAILABLE,
            )
        ],
    )
    await repository.replace_for_requests(
        RequestWarningCode.MAPPING_OVERLAP,
        ["req-1"],
        [
            RequestWarningRecord(
                request_id="req-1", release_id="rel-1", code=RequestWarningCode.MAPPING_OVERLAP
            )
        ],
    )

    codes = {w.code for w in (await repository.list_for_requests(["req-1"]))["req-1"]}
    assert codes == {
        RequestWarningCode.REGRAB_INDEXER_UNAVAILABLE,
        RequestWarningCode.MAPPING_OVERLAP,
    }

    # Clearing MAPPING_OVERLAP must not touch the regrab row.
    await repository.replace_for_requests(RequestWarningCode.MAPPING_OVERLAP, ["req-1"], [])
    codes = {w.code for w in (await repository.list_for_requests(["req-1"]))["req-1"]}
    assert codes == {RequestWarningCode.REGRAB_INDEXER_UNAVAILABLE}


@pytest.mark.asyncio
async def test_delete_for_release_clears_it_for_every_request(
    repository: SqlAlchemyRequestWarningRepository,
    db_manager: DBManager,
) -> None:
    """Deleting release A removes its warning even though SQLite ignores the FK cascade."""

    await _seed_request(db_manager, "req-1")
    await _seed_request(db_manager, "req-2")
    await _seed_release(db_manager, "rel-a")

    await repository.replace_for_requests(
        RequestWarningCode.MAPPING_OVERLAP,
        ["req-1", "req-2"],
        [
            RequestWarningRecord(
                request_id="req-1", release_id="rel-a", code=RequestWarningCode.MAPPING_OVERLAP
            ),
            RequestWarningRecord(
                request_id="req-2", release_id="rel-a", code=RequestWarningCode.MAPPING_OVERLAP
            ),
        ],
    )

    await repository.delete_for_release("rel-a")

    assert await repository.list_for_requests(["req-1", "req-2"]) == {}


@pytest.mark.asyncio
async def test_delete_for_request_release_only_unlinks_one_request(
    repository: SqlAlchemyRequestWarningRepository,
    db_manager: DBManager,
) -> None:
    """Unlinking release A from request R1 must not touch R2's own row for it."""

    await _seed_request(db_manager, "req-1")
    await _seed_request(db_manager, "req-2")
    await _seed_release(db_manager, "rel-a")

    await repository.replace_for_requests(
        RequestWarningCode.MAPPING_OVERLAP,
        ["req-1", "req-2"],
        [
            RequestWarningRecord(
                request_id="req-1", release_id="rel-a", code=RequestWarningCode.MAPPING_OVERLAP
            ),
            RequestWarningRecord(
                request_id="req-2", release_id="rel-a", code=RequestWarningCode.MAPPING_OVERLAP
            ),
        ],
    )

    await repository.delete_for_request_release("req-1", "rel-a")

    by_request = await repository.list_for_requests(["req-1", "req-2"])
    assert set(by_request.keys()) == {"req-2"}


@pytest.mark.asyncio
async def test_list_for_releases_groups_by_release(
    repository: SqlAlchemyRequestWarningRepository,
    db_manager: DBManager,
) -> None:
    await _seed_request(db_manager, "req-1")
    await _seed_release(db_manager, "rel-1")
    await _seed_release(db_manager, "rel-2")

    await repository.replace_for_requests(
        RequestWarningCode.MAPPING_OVERLAP,
        ["req-1"],
        [
            RequestWarningRecord(
                request_id="req-1", release_id="rel-1", code=RequestWarningCode.MAPPING_OVERLAP
            )
        ],
    )
    await repository.replace_for_releases(
        RequestWarningCode.REGRAB_INDEXER_UNAVAILABLE,
        ["rel-2"],
        [
            RequestWarningRecord(
                request_id="req-1",
                release_id="rel-2",
                code=RequestWarningCode.REGRAB_INDEXER_UNAVAILABLE,
                details={"reason": "banned"},
            )
        ],
    )

    by_release = await repository.list_for_releases(["rel-1", "rel-2"])
    assert set(by_release.keys()) == {"rel-1", "rel-2"}
    assert by_release["rel-2"][0].details == {"reason": "banned"}
    assert by_release["rel-1"][0].created_at is not None
