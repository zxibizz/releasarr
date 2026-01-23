"""Tests for the SQLAlchemy-backed release repository."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.application.interfaces.releases import (
    CreateReleaseData,
    FileMappingUpdateData,
    ReleaseFileMapping,
)
from src.db.session import DBManager
from src.domain import models
from src.domain.enums import MediaRequestStatus, MediaType, ReleaseStatus
from src.infrastructure.releases.repository import SqlAlchemyReleaseRepository


@pytest.fixture()
async def engine() -> AsyncEngine:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)  # type: ignore[arg-type]
    yield engine
    await engine.dispose()


@pytest.fixture()
async def session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest.fixture()
async def db_manager(session_factory: async_sessionmaker[AsyncSession]) -> DBManager:
    return DBManager(session_factory)


@pytest.fixture()
async def repository(db_manager: DBManager) -> SqlAlchemyReleaseRepository:
    return SqlAlchemyReleaseRepository(db=db_manager)


@pytest.fixture()
async def seed_requests(db_manager: DBManager) -> Callable[[list[str]], Awaitable[None]]:
    async def _seed(request_ids: list[str]) -> None:
        async with db_manager.transaction() as session:
            for request_id in request_ids:
                session.add(
                    models.MediaRequest(
                        id=request_id,
                        media_type=MediaType.MOVIE,
                        status=MediaRequestStatus.PENDING,
                        title=f"Request {request_id}",
                        year=2024,
                        overview="",
                        poster_url=None,
                        genres=[],
                        runtime_minutes=None,
                        imdb_id=None,
                        season_number=None,
                        total_episodes=None,
                        series_title=None,
                        series_year=None,
                    )
                )

    return _seed


@pytest.mark.asyncio
async def test_create_release_persists_record(
    repository: SqlAlchemyReleaseRepository,
    seed_requests: Callable[[list[str]], Awaitable[None]],
) -> None:
    await seed_requests(["req-1", "req-2"])

    command = CreateReleaseData(
        magnet_link="magnet:?xt=urn:btih:ABCDEF1234567890&dn=Test+Release",
        request_ids=["req-1", "req-2"],
        name="Test Release",
        id="release-test-1",
        source="TestIndexer",
        quality="1080p",
    )

    record = await repository.create_release(command)

    assert record.name == "Test Release"
    assert record.info_hash == "ABCDEF1234567890"
    assert set(record.request_ids) == {"req-1", "req-2"}
    assert record.status is ReleaseStatus.PENDING


@pytest.mark.asyncio
async def test_list_releases_filters_by_status(
    repository: SqlAlchemyReleaseRepository,
    db_manager: DBManager,
) -> None:
    async with db_manager.transaction() as session:
        release = models.Release(
            id="rel-1",
            name="Release 1",
            info_hash="HASH1",
            size_bytes=100,
            status=ReleaseStatus.DOWNLOADING,
            progress=0.5,
            download_speed=1.0,
            upload_speed=0.5,
            seeders=5,
            leechers=2,
            ratio=1.2,
            added_at=datetime.now(UTC),
        )
        session.add(release)

    records, total = await repository.list_releases(
        page=1,
        per_page=20,
        status=ReleaseStatus.DOWNLOADING,
        request_id=None,
    )

    assert total == 1
    assert records[0].id == "rel-1"


@pytest.mark.asyncio
async def test_list_releases_filters_by_request(
    repository: SqlAlchemyReleaseRepository,
    db_manager: DBManager,
    seed_requests: Callable[[list[str]], Awaitable[None]],
) -> None:
    await seed_requests(["req-1"])

    async with db_manager.transaction() as session:
        request = await session.get(models.MediaRequest, "req-1")
        release = models.Release(
            id="rel-1",
            name="Release 1",
            info_hash="HASH1",
            size_bytes=100,
            status=ReleaseStatus.PENDING,
            progress=0.0,
            download_speed=0.0,
            upload_speed=0.0,
            seeders=0,
            leechers=0,
            ratio=0.0,
        )
        if request:
            release.requests.append(request)
        session.add(release)

    records, total = await repository.list_releases(
        page=1,
        per_page=20,
        status=None,
        request_id="req-1",
    )

    assert total == 1
    assert records[0].id == "rel-1"


@pytest.mark.asyncio
async def test_get_release_returns_none_when_missing(
    repository: SqlAlchemyReleaseRepository,
) -> None:
    assert await repository.get_release("missing") is None


@pytest.mark.asyncio
async def test_update_file_mappings_updates_existing_file(
    repository: SqlAlchemyReleaseRepository,
    db_manager: DBManager,
    seed_requests: Callable[[list[str]], Awaitable[None]],
) -> None:
    await seed_requests(["req-1"])

    async with db_manager.transaction() as session:
        release = models.Release(
            id="rel-1",
            name="Release 1",
            info_hash="HASH1",
            size_bytes=100,
            status=ReleaseStatus.PENDING,
            progress=0.0,
            download_speed=0.0,
            upload_speed=0.0,
            seeders=0,
            leechers=0,
            ratio=0.0,
        )
        release.files.append(
            models.ReleaseFile(
                id="file-1",
                name="file.mkv",
                size_bytes=2048,
                path="/downloads/file.mkv",
            )
        )
        session.add(release)

    updates = [
        FileMappingUpdateData(
            file_id="file-1",
            mapping=ReleaseFileMapping(
                mapping_type=MediaType.MOVIE,
                request_id="req-1",
                request_title="Example",
                season=None,
                episode=None,
            ),
        )
    ]

    success = await repository.update_file_mappings("rel-1", updates)
    assert success is True

    refreshed = await repository.get_release("rel-1")
    assert refreshed is not None
    mapping = refreshed.files[0].mapping
    assert mapping is not None
    assert mapping.mapping_type is MediaType.MOVIE
    assert mapping.request_id == "req-1"


@pytest.mark.asyncio
async def test_delete_release_removes_row(
    repository: SqlAlchemyReleaseRepository,
    db_manager: DBManager,
) -> None:
    async with db_manager.transaction() as session:
        session.add(
            models.Release(
                id="rel-1",
                name="Release 1",
                info_hash="HASH1",
                size_bytes=100,
                status=ReleaseStatus.PENDING,
                progress=0.0,
                download_speed=0.0,
                upload_speed=0.0,
                seeders=0,
                leechers=0,
                ratio=0.0,
            )
        )

    assert await repository.delete_release("rel-1") is True
    assert await repository.get_release("rel-1") is None
