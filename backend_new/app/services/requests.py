from __future__ import annotations

from typing import Sequence

from loguru import logger
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.factory import get_clients
from app.models import MediaRequest, RequestStatus, RequestType
from app.schemas.requests import (
    MediaRequestSchema,
    MovieRequestSchema,
    NewMediaRequest,
    RequestsResponse,
    SeriesRequestSchema,
    UpdateMediaRequest,
)


class RequestService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.clients = get_clients()

    async def list_requests(
        self,
        page: int = 1,
        per_page: int = 20,
        status: RequestStatus | None = None,
        type_: RequestType | None = None,
    ) -> RequestsResponse:
        query: Select[tuple[MediaRequest]] = select(MediaRequest)
        count_query: Select[tuple[int]] = select(func.count(MediaRequest.id))

        if status:
            query = query.where(MediaRequest.status == status)
            count_query = count_query.where(MediaRequest.status == status)
        if type_:
            query = query.where(MediaRequest.type == type_)
            count_query = count_query.where(MediaRequest.type == type_)

        query = query.order_by(MediaRequest.created_at.desc())
        query = query.offset((page - 1) * per_page).limit(per_page)

        result: Sequence[MediaRequest] = (await self.session.scalars(query)).all()
        total = await self.session.scalar(count_query)

        return RequestsResponse(
            requests=[self._to_schema(item) for item in result],
            total=total or 0,
            page=page,
            per_page=per_page,
        )

    async def get_request(self, request_id: int) -> MediaRequestSchema | None:
        request_obj = await self.session.get(MediaRequest, request_id)
        if not request_obj:
            return None
        return self._to_schema(request_obj)

    async def create_request(self, payload: NewMediaRequest) -> MediaRequestSchema:
        logger.info("Creating %s request for %s", payload.type, payload.title)

        request_obj = MediaRequest(
            type=RequestType(payload.type),
            title=payload.title,
            year=payload.year,
            poster_url=payload.poster_url,
            overview=payload.overview,
            imdb_id=payload.imdb_id,
        )
        request_obj.set_genre_list(payload.genres)

        if payload.type == RequestType.MOVIE:
            request_obj.runtime = payload.runtime
        else:
            request_obj.series_title = payload.series_title or payload.title
            request_obj.series_year = payload.series_year or payload.year
            request_obj.season_number = payload.season_number
            request_obj.total_episodes = payload.total_episodes
            await self._sync_series_with_external_sources(request_obj, payload)

        self.session.add(request_obj)
        await self.session.commit()
        await self.session.refresh(request_obj)
        return self._to_schema(request_obj)

    async def update_request(
        self, request_id: int, payload: UpdateMediaRequest
    ) -> MediaRequestSchema | None:
        request_obj = await self.session.get(MediaRequest, request_id)
        if not request_obj:
            return None

        for field, value in payload.model_dump(exclude_unset=True).items():
            if field == "genres" and value is not None:
                request_obj.set_genre_list(value)
            elif hasattr(request_obj, field):
                setattr(request_obj, field, value)

        await self.session.commit()
        await self.session.refresh(request_obj)
        return self._to_schema(request_obj)

    async def delete_request(self, request_id: int) -> bool:
        request_obj = await self.session.get(MediaRequest, request_id)
        if not request_obj:
            return False
        await self.session.delete(request_obj)
        await self.session.commit()
        return True

    async def _sync_series_with_external_sources(
        self, request_obj: MediaRequest, payload: NewMediaRequest
    ) -> None:
        if not self.clients.tvdb.enabled:
            return

        tvdb_id = None
        if payload.imdb_id and payload.imdb_id.isdigit():
            tvdb_id = int(payload.imdb_id)

        series_data = None
        if tvdb_id is not None:
            series_data = await self.clients.tvdb.get_series(tvdb_id)
        if series_data:
            request_obj.external_id = str(series_data.get("id"))
            request_obj.poster_url = series_data.get("image") or request_obj.poster_url
            overview = series_data.get("overview")
            request_obj.overview = overview or request_obj.overview
            genres = series_data.get("genres") or []
            if genres:
                request_obj.set_genre_list(genres)
            request_obj.series_title = series_data.get("name") or request_obj.series_title
        if request_obj.external_id and self.clients.sonarr.enabled:
            try:
                await self.clients.sonarr.ensure_series(
                    tvdb_id=int(request_obj.external_id),
                    title=request_obj.series_title or request_obj.title,
                )
            except Exception as exc:  # pragma: no cover - logging only
                logger.warning("Failed to sync Sonarr: %s", exc)

    def _to_schema(self, request_obj: MediaRequest) -> MediaRequestSchema:
        base_kwargs = {
            "id": request_obj.id,
            "title": request_obj.title,
            "year": request_obj.year,
            "poster_url": request_obj.poster_url,
            "overview": request_obj.overview,
            "genres": request_obj.as_genre_list(),
            "status": request_obj.status,
            "created_at": request_obj.created_at,
            "updated_at": request_obj.updated_at,
            "imdb_id": request_obj.imdb_id,
        }
        if request_obj.type == RequestType.MOVIE:
            return MovieRequestSchema.model_validate(
                {
                    **base_kwargs,
                    "type": RequestType.MOVIE,
                    "runtime": request_obj.runtime,
                }
            )
        return SeriesRequestSchema.model_validate(
            {
                **base_kwargs,
                "type": RequestType.SERIES,
                "series_title": request_obj.series_title or request_obj.title,
                "series_year": request_obj.series_year,
                "season_number": request_obj.season_number,
                "total_episodes": request_obj.total_episodes,
            }
        )
