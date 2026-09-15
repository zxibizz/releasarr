"""Tests for the SQLAlchemy-backed release repository."""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.application.interfaces.releases import (
    MANUAL_SOURCE,
    CreateReleaseData,
    FileMappingUpdateData,
    FileReconciliation,
    ReleaseFileMapping,
    ReleaseFileRecord,
)
from src.db import Base
from src.db.session import DBManager
from src.domain import models
from src.domain.enums import MediaRequestStatus, MediaType, ReleaseStatus
from src.infrastructure.releases.repository import SqlAlchemyReleaseRepository


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
        info_url="https://tracker.example/release-test-1",
        published_at=datetime(2026, 1, 1, tzinfo=UTC),
    )

    record = await repository.create_release(command)

    assert record.name == "Test Release"
    assert record.info_hash == "ABCDEF1234567890"
    assert set(record.request_ids) == {"req-1", "req-2"}
    assert record.status is ReleaseStatus.PENDING
    assert record.info_url == "https://tracker.example/release-test-1"
    assert record.published_at == datetime(2026, 1, 1, tzinfo=UTC)


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


@pytest.mark.asyncio
async def test_regrab_candidates_match_any_indexer_but_not_manual_uploads(
    repository: SqlAlchemyReleaseRepository,
    seed_requests: Callable[[list[str]], Awaitable[None]],
    db_manager: DBManager,
) -> None:
    """`torrent_source` holds an indexer name, so only manual uploads are excluded."""

    await seed_requests(["req-1", "req-2"])

    async def _set_status(request_id: str, status: MediaRequestStatus) -> None:
        async with db_manager.transaction() as session:
            request = await session.get(models.MediaRequest, request_id)
            assert request is not None
            request.status = status

    await _set_status("req-1", MediaRequestStatus.MONITORING)

    async def _add(
        release_id: str,
        source: str | None,
        status: ReleaseStatus,
        *,
        request_id: str = "req-1",
    ) -> None:
        async with db_manager.transaction() as session:
            release = models.Release(
                id=release_id,
                name=release_id,
                info_hash=release_id.upper(),
                size_bytes=100,
                status=status,
                progress=1.0,
                download_speed=0.0,
                upload_speed=0.0,
                seeders=1,
                leechers=0,
                ratio=1.0,
                torrent_source=source,
            )
            request = await session.get(models.MediaRequest, request_id)
            assert request is not None
            release.requests = [request]
            session.add(release)

    await _add("from-indexer", "RuTracker", ReleaseStatus.COMPLETED)
    await _add("from-manual", MANUAL_SOURCE, ReleaseStatus.COMPLETED)
    await _add("no-source", None, ReleaseStatus.COMPLETED)
    await _add("still-downloading", "RuTracker", ReleaseStatus.DOWNLOADING)
    # req-2 stays PENDING: a request only reaches monitoring once the release sync
    # confirms nothing is in flight, so a pending request is not a candidate either.
    await _add("pending-request", "RuTracker", ReleaseStatus.COMPLETED, request_id="req-2")

    candidates = await repository.get_potential_outdated_releases()

    assert [record.id for record in candidates] == ["from-indexer"]


async def _seed_release_with_file(
    db_manager: DBManager,
    file_id: str,
    path: str,
    size_bytes: int,
) -> None:
    async with db_manager.transaction() as session:
        release = models.Release(
            id="rel-1",
            name="Release 1",
            info_hash="HASH1",
            size_bytes=100,
            status=ReleaseStatus.COMPLETED,
            progress=1.0,
            download_speed=0.0,
            upload_speed=0.0,
            seeders=1,
            leechers=0,
            ratio=1.0,
        )
        release.files.append(
            models.ReleaseFile(
                id=file_id,
                name=path,
                size_bytes=size_bytes,
                path=path,
            )
        )
        session.add(release)


@pytest.mark.asyncio
async def test_sync_release_files_repoints_a_matched_row_and_keeps_its_mapping(
    repository: SqlAlchemyReleaseRepository,
    db_manager: DBManager,
    seed_requests: Callable[[list[str]], Awaitable[None]],
) -> None:
    """The replacement torrent's own name and size win; the mapping is not its business."""

    await seed_requests(["req-1"])
    await _seed_release_with_file(db_manager, "file-1", "Old/Show.S01E01.mkv", 100)
    await repository.update_file_mappings(
        "rel-1",
        [
            FileMappingUpdateData(
                file_id="file-1",
                mapping=ReleaseFileMapping(
                    mapping_type=MediaType.SERIES,
                    request_id="req-1",
                    request_title="Show - Season 1",
                    season=1,
                    episode=1,
                ),
            )
        ],
    )

    merged = await repository.sync_release_files(
        "rel-1",
        FileReconciliation(
            matched=[
                (
                    "file-1",
                    ReleaseFileRecord(
                        id="incoming-1",
                        name="Repack/Show.S01E01.mkv",
                        size_bytes=4096,
                        path="Repack/Show.S01E01.mkv",
                        mapping=None,
                    ),
                )
            ],
            added=[
                ReleaseFileRecord(
                    id="file-2",
                    name="Repack/Show.S01E02.mkv",
                    size_bytes=2048,
                    path="Repack/Show.S01E02.mkv",
                    mapping=None,
                )
            ],
            missing=[],
        ),
    )

    assert merged is not None
    by_id = {file.id: file for file in merged}
    kept = by_id["file-1"]
    assert kept.path == "Repack/Show.S01E01.mkv"
    assert kept.name == "Repack/Show.S01E01.mkv"
    assert kept.size_bytes == 4096
    assert kept.mapping is not None
    assert (kept.mapping.season, kept.mapping.episode) == (1, 1)
    assert kept.mapping.request_id == "req-1"
    assert by_id["file-2"].mapping is None

    refreshed = await repository.get_release("rel-1")
    assert refreshed is not None
    assert sorted(file.id for file in refreshed.files) == ["file-1", "file-2"]


@pytest.mark.asyncio
async def test_sync_release_files_returns_none_for_a_missing_release(
    repository: SqlAlchemyReleaseRepository,
) -> None:
    result = await repository.sync_release_files(
        "missing", FileReconciliation(matched=[], added=[], missing=[])
    )

    assert result is None
