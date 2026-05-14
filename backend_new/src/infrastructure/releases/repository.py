"""SQLAlchemy-backed implementation of the release repository protocol."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import parse_qs, unquote, urlparse
from uuid import uuid4

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.application.interfaces.releases import (
    CreateReleaseData,
    FileMappingUpdateData,
    ReleaseFileMapping,
    ReleaseFileRecord,
    ReleaseRecord,
    ReleaseRepository,
)
from src.db.session import DBManager
from src.domain import models
from src.domain.enums import ReleaseStatus


@dataclass(slots=True)
class SqlAlchemyReleaseRepository(ReleaseRepository):
    """Repository persisting releases using SQLAlchemy sessions."""

    db: DBManager

    async def list_releases(
        self,
        *,
        page: int,
        per_page: int,
        status: ReleaseStatus | None,
        request_id: str | None,
    ) -> tuple[list[ReleaseRecord], int]:
        async with self.db.session() as session:
            filters = []
            if status is not None:
                filters.append(models.Release.status == status)

            if request_id is not None:
                filters.append(models.Release.requests.any(models.MediaRequest.id == request_id))

            total = await self._count_releases(session, filters)

            stmt: Select[tuple[models.Release]] = (
                select(models.Release)
                .options(
                    selectinload(models.Release.files),
                    selectinload(models.Release.requests),
                )
                .where(*filters)
                .order_by(models.Release.added_at.desc())
                .offset((page - 1) * per_page)
                .limit(per_page)
            )

            result = await session.execute(stmt)
            records = [self._to_record(release) for release in result.scalars().all()]
            return records, total

    async def create_release(self, data: CreateReleaseData) -> ReleaseRecord:
        info_hash, display_name = self._parse_magnet(data.magnet_link)
        async with self.db.transaction() as session:
            release_model = models.Release(
                id=uuid4().hex,
                name=display_name,
                info_hash=info_hash,
                size_bytes=0,
                status=ReleaseStatus.PENDING,
                progress=0.0,
                download_speed=0.0,
                upload_speed=0.0,
                seeders=0,
                leechers=0,
                ratio=0.0,
                torrent_source="magnet",
                quality=None,
            )
            release_model.requests = []
            session.add(release_model)

            if data.request_ids:
                requests = await self._load_requests(session, data.request_ids)
                if len(requests) != len(set(data.request_ids)):
                    missing = set(data.request_ids) - {request.id for request in requests}
                    msg = f"Media requests not found: {sorted(missing)}"
                    raise ValueError(msg)
                release_model.requests.extend(requests)

            await session.flush()
            await session.refresh(
                release_model,
                attribute_names=["files", "requests"],
            )
            return self._to_record(release_model)

    async def get_release(self, release_id: str) -> ReleaseRecord | None:
        async with self.db.session() as session:
            release = await session.get(
                models.Release,
                release_id,
                options=[
                    selectinload(models.Release.files),
                    selectinload(models.Release.requests),
                ],
            )
            if release is None:
                return None
            return self._to_record(release)

    async def delete_release(self, release_id: str) -> bool:
        async with self.db.transaction() as session:
            release = await session.get(models.Release, release_id)
            if release is None:
                return False
            await session.delete(release)
            return True

    async def update_file_mappings(
        self,
        release_id: str,
        updates: list[FileMappingUpdateData],
    ) -> bool:
        if not updates:
            return True

        async with self.db.transaction() as session:
            release = await session.get(
                models.Release,
                release_id,
                options=[selectinload(models.Release.files), selectinload(models.Release.requests)],
            )
            if release is None:
                return False

            files_lookup = {file.id: file for file in release.files}

            for update in updates:
                file = files_lookup.get(update.file_id)
                if file is None:
                    return False

                mapping = update.mapping
                if mapping is None:
                    file.mapping_type = None
                    file.mapped_request_id = None
                    file.mapped_request_title = None
                    file.season = None
                    file.episode = None
                else:
                    file.mapping_type = mapping.mapping_type
                    file.mapped_request_id = mapping.request_id
                    file.mapped_request_title = mapping.request_title
                    file.season = mapping.season
                    file.episode = mapping.episode

                    if mapping.request_id and mapping.request_id not in {
                        req.id for req in release.requests
                    }:
                        request = await session.get(models.MediaRequest, mapping.request_id)
                        if request is not None:
                            release.requests.append(request)

            await session.flush()
            return True

    async def _count_releases(
        self,
        session: AsyncSession,
        filters: Sequence[object],
    ) -> int:
        stmt = select(func.count(models.Release.id)).where(*filters)
        result = await session.execute(stmt)
        return int(result.scalar() or 0)

    async def _load_requests(
        self,
        session: AsyncSession,
        request_ids: Iterable[str],
    ) -> list[models.MediaRequest]:
        if not request_ids:
            return []
        stmt = select(models.MediaRequest).where(models.MediaRequest.id.in_(set(request_ids)))
        result = await session.execute(stmt)
        return result.scalars().all()

    def _parse_magnet(self, magnet_link: str) -> tuple[str, str]:
        parsed = urlparse(magnet_link)
        if parsed.scheme != "magnet":
            msg = "magnet_link must be a magnet URI"
            raise ValueError(msg)

        params = parse_qs(parsed.query)
        xt_values = params.get("xt", [])
        info_hash = None
        for value in xt_values:
            if value.startswith("urn:btih:"):
                info_hash = value.split(":")[-1].upper()
                break
        if info_hash is None:
            msg = "magnet_link missing info hash"
            raise ValueError(msg)

        display_name = ""
        dn_values = params.get("dn", [])
        if dn_values:
            display_name = unquote(dn_values[0])
        if not display_name:
            display_name = info_hash

        return info_hash, display_name

    def _to_record(self, release: models.Release) -> ReleaseRecord:
        files = [self._to_file_record(file) for file in release.files]
        request_ids = [request.id for request in release.requests]
        return ReleaseRecord(
            id=release.id,
            name=release.name,
            info_hash=release.info_hash,
            size_bytes=release.size_bytes,
            status=release.status,
            progress=release.progress,
            download_speed=release.download_speed,
            upload_speed=release.upload_speed,
            seeders=release.seeders,
            leechers=release.leechers,
            ratio=release.ratio,
            added_at=self._ensure_datetime(release.added_at),
            completed_at=self._ensure_datetime(release.completed_at),
            request_ids=request_ids,
            torrent_source=release.torrent_source,
            quality=release.quality,
            files=files,
        )

    def _to_file_record(self, file: models.ReleaseFile) -> ReleaseFileRecord:
        mapping = None
        if file.mapping_type or file.mapped_request_id:
            mapping = ReleaseFileMapping(
                mapping_type=file.mapping_type,
                request_id=file.mapped_request_id,
                request_title=file.mapped_request_title,
                season=file.season,
                episode=file.episode,
            )
        return ReleaseFileRecord(
            id=file.id,
            name=file.name,
            size_bytes=file.size_bytes,
            path=file.path,
            mapping=mapping,
        )

    def _ensure_datetime(self, value: datetime | None) -> datetime | None:
        return value


__all__ = ["SqlAlchemyReleaseRepository"]
