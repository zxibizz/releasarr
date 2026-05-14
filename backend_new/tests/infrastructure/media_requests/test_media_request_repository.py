"""Tests for the SQLAlchemy-backed media request repository."""

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

from src.application.interfaces.media_requests import (
    CreateMediaRequestData,
    UpdateMediaRequestData,
)
from src.db.session import DBManager
from src.domain import models
from src.domain.enums import MediaRequestStatus, MediaType
from src.infrastructure.media_requests.repository import SqlAlchemyMediaRequestRepository


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
async def repository(db_manager: DBManager) -> SqlAlchemyMediaRequestRepository:
    return SqlAlchemyMediaRequestRepository(db=db_manager)


@pytest.fixture()
async def seed_request(
    db_manager: DBManager,
) -> Callable[[str, MediaRequestStatus, MediaType], Awaitable[None]]:
    async def _seed(
        request_id: str,
        status: MediaRequestStatus,
        media_type: MediaType,
    ) -> None:
        async with db_manager.transaction() as session:
            session.add(
                models.MediaRequest(
                    id=request_id,
                    media_type=media_type,
                    status=status,
                    title=f"Title {request_id}",
                    year=2024,
                    overview="Overview",
                    poster_url=None,
                    genres=["drama"],
                    runtime_minutes=120,
                    imdb_id="tt0000001",
                    season_number=None,
                    total_episodes=None,
                    series_title=None,
                    series_year=None,
                    created_at=datetime.now(UTC),
                    updated_at=datetime.now(UTC),
                )
            )

    return _seed


@pytest.mark.asyncio
async def test_create_request_persists_data(repository: SqlAlchemyMediaRequestRepository) -> None:
    data = CreateMediaRequestData(
        id="req-1",
        media_type=MediaType.MOVIE,
        title="Example",
        year=2024,
        overview="",
        poster_url="http://example.test/poster.jpg",
        genres=["action"],
        runtime_minutes=120,
        imdb_id="tt1234567",
        season_number=None,
        total_episodes=None,
        series_title=None,
        series_year=None,
        status=MediaRequestStatus.PENDING,
    )

    record = await repository.create_request(data)

    assert record.id == "req-1"
    assert record.media_type is MediaType.MOVIE
    assert record.genres == ["action"]


@pytest.mark.asyncio
async def test_list_requests_supports_filters(
    repository: SqlAlchemyMediaRequestRepository,
    seed_request: Callable[[str, MediaRequestStatus, MediaType], Awaitable[None]],
) -> None:
    await seed_request("req-1", MediaRequestStatus.PENDING, MediaType.MOVIE)
    await seed_request("req-2", MediaRequestStatus.COMPLETED, MediaType.SERIES)

    page, total = await repository.list_requests(
        page=1,
        per_page=10,
        status=MediaRequestStatus.COMPLETED,
        media_type=MediaType.SERIES,
    )

    assert total == 1
    assert page[0].id == "req-2"


@pytest.mark.asyncio
async def test_get_request_returns_none_when_missing(
    repository: SqlAlchemyMediaRequestRepository,
) -> None:
    assert await repository.get_request("missing") is None


@pytest.mark.asyncio
async def test_update_request_modifies_fields(
    repository: SqlAlchemyMediaRequestRepository,
    seed_request: Callable[[str, MediaRequestStatus, MediaType], Awaitable[None]],
) -> None:
    await seed_request("req-1", MediaRequestStatus.PENDING, MediaType.MOVIE)

    update = UpdateMediaRequestData(
        title="Updated",
        year=2025,
        genres=["thriller"],
        status=MediaRequestStatus.SEARCHING,
    )

    record = await repository.update_request("req-1", update)
    assert record is not None
    assert record.title == "Updated"
    assert record.year == 2025
    assert record.status is MediaRequestStatus.SEARCHING
    assert record.genres == ["thriller"]


@pytest.mark.asyncio
async def test_update_request_returns_none_for_missing(
    repository: SqlAlchemyMediaRequestRepository,
) -> None:
    update = UpdateMediaRequestData(title="Updated")
    assert await repository.update_request("missing", update) is None


@pytest.mark.asyncio
async def test_delete_request_removes_row(
    repository: SqlAlchemyMediaRequestRepository,
    seed_request: Callable[[str, MediaRequestStatus, MediaType], Awaitable[None]],
) -> None:
    await seed_request("req-1", MediaRequestStatus.PENDING, MediaType.MOVIE)

    assert await repository.delete_request("req-1") is True
    assert await repository.get_request("req-1") is None
