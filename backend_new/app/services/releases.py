from __future__ import annotations

from datetime import datetime
from typing import Sequence

from loguru import logger
from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.clients.factory import get_clients
from app.models import MediaRequest, Release, ReleaseFile
from app.schemas.common import Release as ReleaseSchema
from app.schemas.common import ReleaseFile as ReleaseFileSchema
from app.schemas.releases import SuccessResponse, UpdateFileMapping


class ReleaseService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.clients = get_clients()

    async def list_releases(
        self,
        status: str | None = None,
        request_id: int | None = None,
    ) -> list[ReleaseSchema]:
        query: Select[tuple[Release]] = select(Release)
        if status:
            query = query.where(Release.status == status)
        if request_id:
            query = query.join(Release.requests).where(MediaRequest.id == request_id)
        query = query.order_by(Release.added_date.desc())
        query = query.options(
            selectinload(Release.requests),
            selectinload(Release.files),
            selectinload(Release.file_matchings),
        )
        releases: Sequence[Release] = (await self.session.scalars(query)).all()
        return [self._to_schema(release) for release in releases]

    async def get_release(self, release_id: int) -> ReleaseSchema | None:
        release = await self.session.get(Release, release_id)
        if not release:
            return None
        await self.session.refresh(
            release, attribute_names=["requests", "files", "file_matchings"]
        )
        return self._to_schema(release)

    async def get_request_releases(self, request_id: int) -> list[ReleaseSchema]:
        query = (
            select(Release)
            .join(Release.requests)
            .where(MediaRequest.id == request_id)
            .options(
                selectinload(Release.requests),
                selectinload(Release.files),
                selectinload(Release.file_matchings),
            )
        )
        releases = (await self.session.scalars(query)).all()
        return [self._to_schema(release) for release in releases]

    async def create_release(
        self,
        name: str,
        request_ids: list[int],
        size: int = 0,
        torrent_source: str | None = None,
        quality: str | None = None,
    ) -> ReleaseSchema:
        release = Release(
            name=name,
            size=size,
            torrent_source=torrent_source,
            quality=quality,
            status="pending",
            added_date=datetime.utcnow(),
            search=name,
        )
        if request_ids:
            related_requests = (
                await self.session.scalars(
                    select(MediaRequest).where(MediaRequest.id.in_(request_ids))
                )
            ).all()
            release.requests = list(related_requests)
        self.session.add(release)
        await self.session.commit()
        await self.session.refresh(release, attribute_names=["requests", "files"])
        return self._to_schema(release)

    async def delete_release(self, release_id: int) -> bool:
        release = await self.session.get(Release, release_id)
        if not release:
            return False
        await self.session.delete(release)
        await self.session.commit()
        return True

    async def pause_release(self, release_id: int) -> bool:
        release = await self.session.get(Release, release_id)
        if not release:
            return False
        release.status = "pending"
        release.download_speed = 0
        await self.session.commit()
        return True

    async def resume_release(self, release_id: int) -> bool:
        release = await self.session.get(Release, release_id)
        if not release:
            return False
        release.status = "downloading"
        await self.session.commit()
        return True

    async def update_file_mapping(
        self, release_id: int, file_id: int, mapping: UpdateFileMapping
    ) -> SuccessResponse | None:
        file = await self.session.get(ReleaseFile, file_id)
        if not file or file.release_id != release_id:
            return None
        request_mapping = mapping.request_mapping or {}
        request_id = request_mapping.get("request_id")
        if request_id:
            file.request_id = int(request_id)
        file.season = (mapping.episode_mapping or {}).get("season")
        file.episode = (mapping.episode_mapping or {}).get("episode")
        await self.session.commit()
        return SuccessResponse()

    async def attach_torrent(
        self,
        release_id: int,
        download_url: str,
        request_save_path: str | None = None,
    ) -> bool:
        release = await self.session.get(Release, release_id)
        if not release:
            return False
        if not self.clients.prowlarr.enabled or not self.clients.qbittorrent.enabled:
            logger.info("Skipping torrent download; external clients disabled")
            return False

        torrent_data = await self.clients.prowlarr.download_torrent(download_url)
        await self.clients.qbittorrent.add_torrent(
            torrent_data, save_path=request_save_path
        )
        release.status = "downloading"
        await self.session.commit()
        return True

    def _to_schema(self, release: Release) -> ReleaseSchema:
        request_ids = [req.id for req in release.requests]
        files = [
            ReleaseFileSchema(
                id=file.id,
                name=file.name,
                path=file.path,
                size=file.size,
                episode_mapping=None,
                request_mapping=None,
            )
            for file in release.files
        ]
        return ReleaseSchema(
            id=release.id,
            name=release.name,
            hash=release.hash,
            size=release.size,
            files=files,
            status=release.status,
            progress=release.progress,
            download_speed=release.download_speed,
            upload_speed=release.upload_speed,
            seeders=release.seeders,
            leechers=release.leechers,
            ratio=release.ratio,
            added_date=release.added_date,
            completed_date=release.completed_date,
            request_ids=request_ids,
            torrent_source=release.torrent_source,
            quality=release.quality,
        )
