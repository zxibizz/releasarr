"""Tests for the SQLAlchemy-backed media request repository."""

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

from src.application.interfaces.media_requests import (
    CreateMediaRequestData,
    UpdateMediaRequestData,
)
from src.db import Base
from src.db.session import DBManager
from src.domain import models
from src.domain.enums import MediaRequestStatus, MediaType, RequestSort, RequestWarningCode
from src.infrastructure.media_requests.repository import SqlAlchemyMediaRequestRepository


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
async def test_list_requests_filters_by_has_warnings(
    repository: SqlAlchemyMediaRequestRepository,
    db_manager: DBManager,
    seed_request: Callable[[str, MediaRequestStatus, MediaType], Awaitable[None]],
) -> None:
    await seed_request("req-1", MediaRequestStatus.PENDING, MediaType.MOVIE)
    await seed_request("req-2", MediaRequestStatus.PENDING, MediaType.MOVIE)

    async with db_manager.transaction() as session:
        session.add(
            models.RequestWarning(
                id="warn-1",
                request_id="req-1",
                release_id=None,
                code=RequestWarningCode.REGRAB_INDEXER_UNAVAILABLE,
            )
        )

    warned, warned_total = await repository.list_requests(
        page=1, per_page=10, status=None, media_type=None, has_warnings=True
    )
    assert warned_total == 1
    assert [record.id for record in warned] == ["req-1"]

    clean, clean_total = await repository.list_requests(
        page=1, per_page=10, status=None, media_type=None, has_warnings=False
    )
    assert clean_total == 1
    assert [record.id for record in clean] == ["req-2"]


@pytest.mark.asyncio
async def test_get_request_returns_none_when_missing(
    repository: SqlAlchemyMediaRequestRepository,
) -> None:
    assert await repository.get_request("missing") is None


@pytest.mark.asyncio
async def test_record_reports_stored_newest_release_publication_date(
    repository: SqlAlchemyMediaRequestRepository,
    seed_request: Callable[[str, MediaRequestStatus, MediaType], Awaitable[None]],
) -> None:
    await seed_request("req-1", MediaRequestStatus.PENDING, MediaType.MOVIE)

    published_at = datetime(2026, 3, 1, tzinfo=UTC)
    await repository.update_request(
        "req-1",
        UpdateMediaRequestData(newest_release_published_at=published_at),
    )

    record = await repository.get_request("req-1")
    assert record is not None
    assert record.newest_release_published_at == published_at


@pytest.mark.asyncio
async def test_record_has_no_release_publication_date_by_default(
    repository: SqlAlchemyMediaRequestRepository,
    seed_request: Callable[[str, MediaRequestStatus, MediaType], Awaitable[None]],
) -> None:
    await seed_request("req-1", MediaRequestStatus.PENDING, MediaType.MOVIE)

    record = await repository.get_request("req-1")
    assert record is not None
    assert record.newest_release_published_at is None


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
async def test_update_request_clears_nullable_field(
    repository: SqlAlchemyMediaRequestRepository,
    seed_request: Callable[[str, MediaRequestStatus, MediaType], Awaitable[None]],
) -> None:
    await seed_request("req-1", MediaRequestStatus.PENDING, MediaType.MOVIE)

    # Explicit None must clear the column, while omitted fields are preserved.
    update = UpdateMediaRequestData(overview=None)
    record = await repository.update_request("req-1", update)

    assert record is not None
    assert record.overview is None
    assert record.imdb_id == "tt0000001"
    assert record.title == "Title req-1"


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


async def _seed_titled(
    db_manager: DBManager,
    request_id: str,
    *,
    title: str,
    series_title: str | None = None,
    status: MediaRequestStatus = MediaRequestStatus.PENDING,
) -> None:
    async with db_manager.transaction() as session:
        session.add(
            models.MediaRequest(
                id=request_id,
                media_type=MediaType.SERIES if series_title else MediaType.MOVIE,
                status=status,
                title=title,
                year=2024,
                overview=None,
                poster_url=None,
                genres=[],
                runtime_minutes=None,
                imdb_id=None,
                season_number=1 if series_title else None,
                total_episodes=10 if series_title else None,
                series_title=series_title,
                series_year=None,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
        )


@pytest.mark.asyncio
async def test_list_requests_searches_both_titles_case_insensitively(
    repository: SqlAlchemyMediaRequestRepository,
    db_manager: DBManager,
) -> None:
    await _seed_titled(db_manager, "req-1", title="Arrival")
    await _seed_titled(
        db_manager, "req-2", title="Example Show - Season 1", series_title="Example Show"
    )
    await _seed_titled(db_manager, "req-3", title="Dune")

    records, total = await repository.list_requests(
        page=1, per_page=10, status=None, media_type=None, search="example show"
    )

    assert total == 1
    # The series title matched; the request's own title only carries it as a suffix.
    assert [record.id for record in records] == ["req-2"]


@pytest.mark.asyncio
async def test_list_requests_search_treats_wildcards_as_literal_text(
    repository: SqlAlchemyMediaRequestRepository,
    db_manager: DBManager,
) -> None:
    await _seed_titled(db_manager, "req-1", title="100% Complete")
    await _seed_titled(db_manager, "req-2", title="1000 Ways")

    records, total = await repository.list_requests(
        page=1, per_page=10, status=None, media_type=None, search="100%"
    )

    assert total == 1
    assert [record.id for record in records] == ["req-1"]


@pytest.mark.asyncio
async def test_list_requests_active_only_excludes_completed(
    repository: SqlAlchemyMediaRequestRepository,
    db_manager: DBManager,
) -> None:
    await _seed_titled(db_manager, "req-1", title="One")
    await _seed_titled(db_manager, "req-2", title="Two", status=MediaRequestStatus.COMPLETED)
    await _seed_titled(db_manager, "req-3", title="Three", status=MediaRequestStatus.DOWNLOADING)

    records, total = await repository.list_requests(
        page=1, per_page=10, status=None, media_type=None, active_only=True
    )

    assert total == 2
    assert {record.id for record in records} == {"req-1", "req-3"}


@pytest.mark.asyncio
async def test_list_requests_sorts_by_title(
    repository: SqlAlchemyMediaRequestRepository,
    db_manager: DBManager,
) -> None:
    await _seed_titled(db_manager, "req-1", title="Beta")
    await _seed_titled(db_manager, "req-2", title="alpha")
    await _seed_titled(db_manager, "req-3", title="Gamma")

    ascending, _ = await repository.list_requests(
        page=1, per_page=10, status=None, media_type=None, sort=RequestSort.TITLE_ASC
    )
    descending, _ = await repository.list_requests(
        page=1, per_page=10, status=None, media_type=None, sort=RequestSort.TITLE_DESC
    )

    # Both backends order by bytes: capitals before lowercase.
    assert [record.title for record in ascending] == ["Beta", "Gamma", "alpha"]
    assert [record.title for record in descending] == ["alpha", "Gamma", "Beta"]
