"""SQLAlchemy-backed media request repository implementation."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, fields

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.interfaces.media_requests import (
    CreateMediaRequestData,
    MediaLocalization,
    MediaRequestRecord,
    MediaRequestRepository,
    UpdateMediaRequestData,
)
from src.db.session import DBManager
from src.domain import models
from src.domain.enums import MediaRequestStatus, MediaType


@dataclass(slots=True)
class SqlAlchemyMediaRequestRepository(MediaRequestRepository):
    """Persist media requests using SQLAlchemy sessions."""

    db: DBManager

    async def list_requests(
        self,
        *,
        page: int,
        per_page: int,
        status: MediaRequestStatus | None,
        media_type: MediaType | None,
    ) -> tuple[list[MediaRequestRecord], int]:
        async with self.db.session() as session:
            filters = []
            if status is not None:
                filters.append(models.MediaRequest.status == status)
            if media_type is not None:
                filters.append(models.MediaRequest.media_type == media_type)

            total = await self._count_requests(session, filters)

            stmt: Select[tuple[models.MediaRequest]] = (
                select(models.MediaRequest)
                .where(*filters)
                .order_by(models.MediaRequest.created_at.desc())
                .offset((page - 1) * per_page)
                .limit(per_page)
            )
            result = await session.execute(stmt)
            records = [self._to_record(request) for request in result.scalars().all()]
            return records, total

    async def create_request(self, data: CreateMediaRequestData) -> MediaRequestRecord:
        async with self.db.transaction() as session:
            request = models.MediaRequest(
                id=data.id,
                media_type=data.media_type,
                status=data.status,
                title=data.title,
                year=data.year,
                overview=data.overview,
                poster_url=data.poster_url,
                genres=list(data.genres),
                localizations=self._serialize_localizations(data.localizations),
                runtime_minutes=data.runtime_minutes,
                imdb_id=data.imdb_id,
                season_number=data.season_number,
                total_episodes=data.total_episodes,
                series_title=data.series_title,
                series_year=data.series_year,
                sonarr_series_id=data.sonarr_series_id,
            )
            session.add(request)
            await session.flush()
            await session.refresh(request)
            return self._to_record(request)

    async def get_request(self, request_id: str) -> MediaRequestRecord | None:
        async with self.db.session() as session:
            request = await session.get(models.MediaRequest, request_id)
            if request is None:
                return None
            return self._to_record(request)

    async def update_request(
        self,
        request_id: str,
        data: UpdateMediaRequestData,
    ) -> MediaRequestRecord | None:
        async with self.db.transaction() as session:
            request = await session.get(models.MediaRequest, request_id)
            if request is None:
                return None

            for field in fields(UpdateMediaRequestData):
                if field.name == "localizations":
                    continue
                value = getattr(data, field.name)
                if value is None:
                    continue
                setattr(request, field.name, value)

            if data.localizations is not None:
                request.localizations = self._serialize_localizations(data.localizations)

            await session.flush()
            await session.refresh(request)
            return self._to_record(request)

    async def delete_request(self, request_id: str) -> bool:
        async with self.db.transaction() as session:
            request = await session.get(models.MediaRequest, request_id)
            if request is None:
                return False
            await session.delete(request)
            return True

    async def find_by_sonarr(
        self,
        *,
        sonarr_series_id: int,
        season_number: int,
    ) -> MediaRequestRecord | None:
        async with self.db.session() as session:
            stmt = select(models.MediaRequest).where(
                models.MediaRequest.sonarr_series_id == sonarr_series_id,
                models.MediaRequest.season_number == season_number,
            )
            result = await session.execute(stmt)
            request = result.scalar_one_or_none()
            if request is None:
                return None
            return self._to_record(request)

    async def list_sonarr_requests(self) -> list[MediaRequestRecord]:
        async with self.db.session() as session:
            stmt: Select[tuple[models.MediaRequest]] = select(models.MediaRequest).where(
                models.MediaRequest.sonarr_series_id.is_not(None)
            )
            result = await session.execute(stmt)
            return [self._to_record(request) for request in result.scalars().all()]

    async def _count_requests(
        self,
        session: AsyncSession,
        filters: Sequence[object],
    ) -> int:
        stmt = select(func.count(models.MediaRequest.id)).where(*filters)
        result = await session.execute(stmt)
        return int(result.scalar() or 0)

    def _to_record(self, request: models.MediaRequest) -> MediaRequestRecord:
        localizations = self._deserialize_localizations(request.localizations)
        return MediaRequestRecord(
            id=request.id,
            media_type=request.media_type,
            status=request.status,
            title=request.title,
            year=request.year,
            overview=request.overview,
            poster_url=request.poster_url,
            genres=list(request.genres or []),
            localizations=localizations,
            runtime_minutes=request.runtime_minutes,
            imdb_id=request.imdb_id,
            season_number=request.season_number,
            total_episodes=request.total_episodes,
            series_title=request.series_title,
            series_year=request.series_year,
            sonarr_series_id=request.sonarr_series_id,
            created_at=request.created_at,
            updated_at=request.updated_at,
        )

    def _serialize_localizations(
        self,
        localizations: dict[str, MediaLocalization],
    ) -> dict[str, dict[str, str | None]]:
        if not localizations:
            return {}
        result: dict[str, dict[str, str | None]] = {}
        for language, localization in localizations.items():
            if not language:
                continue
            key = str(language).lower()
            result[key] = {
                "title": localization.title,
                "overview": localization.overview,
            }
        return result

    def _deserialize_localizations(
        self,
        raw: dict[str, dict[str, object]] | None,
    ) -> dict[str, MediaLocalization]:
        if not raw:
            return {}
        result: dict[str, MediaLocalization] = {}
        for language, payload in raw.items():
            if not isinstance(payload, dict):
                continue
            key = str(language).lower()
            title = payload.get("title")
            overview = payload.get("overview")
            result[key] = MediaLocalization(
                title=str(title) if title is not None else None,
                overview=str(overview) if overview is not None else None,
            )
        return result


__all__ = ["SqlAlchemyMediaRequestRepository"]
