"""SQLAlchemy-backed implementation of the release repository protocol."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.application.interfaces.releases import (
    MANUAL_SOURCE,
    MAX_EXPORT_FAILURES,
    CreateReleaseData,
    FileMappingUpdateData,
    FileReconciliation,
    ReleaseFileMapping,
    ReleaseFileRecord,
    ReleaseRecord,
    ReleaseRepository,
    ReleaseRequestSnapshot,
)
from src.application.utility.magnet import parse_magnet
from src.db.datetimes import as_utc
from src.db.repository import BaseSqlAlchemyRepository, Filter
from src.domain import models
from src.domain.enums import MediaRequestStatus, ReleaseStatus, RequestWarningCode


@dataclass(slots=True)
class SqlAlchemyReleaseRepository(BaseSqlAlchemyRepository, ReleaseRepository):
    """Repository persisting releases using SQLAlchemy sessions."""

    async def list_releases(
        self,
        *,
        page: int,
        per_page: int,
        status: ReleaseStatus | None,
        request_id: str | None,
    ) -> tuple[list[ReleaseRecord], int]:
        async with self.db.session() as session:
            filters: list[Filter] = []
            if status is not None:
                filters.append(models.Release.status == status)

            if request_id is not None:
                filters.append(models.Release.requests.any(models.MediaRequest.id == request_id))

            total = await self._count(session, models.Release.id, filters)

            stmt: Select[tuple[models.Release]] = self._paginate(
                select(models.Release)
                .options(
                    selectinload(models.Release.files),
                    selectinload(models.Release.requests),
                )
                .where(*filters)
                .order_by(models.Release.added_at.desc()),
                page=page,
                per_page=per_page,
            )

            result = await session.execute(stmt)
            records = [self._to_record(release) for release in result.scalars().all()]
            return records, total

    async def create_release(self, data: CreateReleaseData) -> ReleaseRecord:
        info_hash = parse_magnet(data.magnet_link).info_hash
        release_id = data.id
        release_name = data.name
        torrent_source = data.source
        quality = data.quality
        async with self.db.transaction() as session:
            release_model = models.Release(
                id=release_id,
                name=release_name,
                info_hash=info_hash,
                size_bytes=0,
                status=ReleaseStatus.PENDING,
                progress=0.0,
                download_speed=0.0,
                upload_speed=0.0,
                seeders=0,
                leechers=0,
                ratio=0.0,
                torrent_source=torrent_source,
                quality=quality,
                info_url=data.info_url,
                published_at=data.published_at,
                search_query=data.search_query,
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

            if data.files:
                for file_record in data.files:
                    file_model = models.ReleaseFile(
                        id=file_record.id,
                        release_id=release_id,
                        name=file_record.name,
                        size_bytes=file_record.size_bytes,
                        path=file_record.path,
                    )
                    session.add(file_model)

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

    async def unlink_request(self, release_id: str, request_id: str) -> bool:
        async with self.db.transaction() as session:
            release = await session.get(
                models.Release,
                release_id,
                options=[selectinload(models.Release.requests)],
            )
            if release is None:
                return False
            remaining = [req for req in release.requests if req.id != request_id]
            release.requests = remaining
            await session.flush()
            return True

    async def get_releases_for_requests(self, request_ids: list[str]) -> list[ReleaseRecord]:
        if not request_ids:
            return []
        async with self.db.session() as session:
            stmt = (
                select(models.Release)
                .where(models.Release.requests.any(models.MediaRequest.id.in_(request_ids)))
                .options(
                    selectinload(models.Release.files),
                    selectinload(models.Release.requests),
                )
            )
            result = await session.execute(stmt)
            return [self._to_record(release) for release in result.scalars().all()]

    async def list_request_ids_with_releases(self) -> list[str]:
        async with self.db.session() as session:
            stmt = select(models.RELEASE_REQUEST_LINKS.c.request_id).distinct()
            result = await session.execute(stmt)
            return [row[0] for row in result.all()]

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

    async def sync_release_files(
        self,
        release_id: str,
        reconciliation: FileReconciliation,
    ) -> list[ReleaseFileRecord] | None:
        async with self.db.transaction() as session:
            release = await session.get(
                models.Release,
                release_id,
                options=[selectinload(models.Release.files)],
            )
            if release is None:
                return None

            files_by_id = {file.id: file for file in release.files}

            for existing_id, incoming in reconciliation.matched:
                stored = files_by_id.get(existing_id)
                if stored is None:
                    continue
                # Only what describes the file on disk is rewritten. Every mapping
                # column belongs to whoever filled it in, and a replacement torrent
                # is not a reason to review that.
                stored.name = incoming.name
                stored.size_bytes = incoming.size_bytes
                stored.path = incoming.path

            for record in reconciliation.added:
                release.files.append(
                    models.ReleaseFile(
                        id=record.id,
                        release_id=release_id,
                        name=record.name,
                        size_bytes=record.size_bytes,
                        path=record.path,
                    )
                )

            await session.flush()
            return [self._to_file_record(file) for file in release.files]

    async def get_finished_not_exported(self) -> list[ReleaseRecord]:
        async with self.db.session() as session:
            stmt = (
                select(models.Release)
                .options(
                    selectinload(models.Release.files),
                    selectinload(models.Release.requests),
                )
                .where(
                    models.Release.status == ReleaseStatus.COMPLETED,
                    models.Release.export_failures_count < MAX_EXPORT_FAILURES,
                    (models.Release.last_exported_info_hash != models.Release.info_hash)
                    | (models.Release.last_exported_info_hash.is_(None)),
                )
            )
            result = await session.execute(stmt)
            return [self._to_record(release) for release in result.scalars().all()]

    async def get_potential_outdated_releases(self) -> list[ReleaseRecord]:
        async with self.db.session() as session:
            # Anything but a hand-supplied torrent came from an indexer we can
            # search again; `torrent_source` holds that indexer's name, so it
            # cannot be matched against a fixed provider string. The release sync
            # already only leaves a request on `monitoring` once it holds a release
            # matching those conditions, so that status is the request-side filter.
            #
            # A release that already refused its replacement is left out entirely:
            # the indexer's answer is not going to change between two hourly
            # passes, and a check costs a search plus the torrent file it has to
            # download before it can compare files. The on-demand refresh is what
            # retries one, and a replacement that finally carries every stored file
            # clears the row, which is what puts it back in here.
            refused_replacement = (
                select(models.RequestWarning.id)
                .where(
                    models.RequestWarning.release_id == models.Release.id,
                    models.RequestWarning.code == RequestWarningCode.REGRAB_FILES_MISSING,
                )
                .exists()
            )
            stmt = (
                select(models.Release)
                .join(models.Release.requests)
                .options(
                    selectinload(models.Release.files),
                    selectinload(models.Release.requests),
                )
                .where(
                    models.Release.status == ReleaseStatus.COMPLETED,
                    models.Release.torrent_source.is_not(None),
                    models.Release.torrent_source != MANUAL_SOURCE,
                    models.MediaRequest.status == MediaRequestStatus.MONITORING,
                    ~refused_replacement,
                )
                .distinct()
            )
            result = await session.execute(stmt)
            return [self._to_record(release) for release in result.scalars().all()]

    async def update_release(self, release_id: str, **kwargs: object) -> bool:
        async with self.db.transaction() as session:
            release = await session.get(models.Release, release_id)
            if release is None:
                return False

            for key, value in kwargs.items():
                if hasattr(release, key):
                    setattr(release, key, value)

            return True

    async def _load_requests(
        self,
        session: AsyncSession,
        request_ids: Iterable[str],
    ) -> list[models.MediaRequest]:
        if not request_ids:
            return []
        stmt = select(models.MediaRequest).where(models.MediaRequest.id.in_(set(request_ids)))
        result = await session.execute(stmt)
        return list(result.scalars().all())

    def _to_request_snapshot(self, request: models.MediaRequest) -> ReleaseRequestSnapshot:
        alternate_titles: list[str] = []
        for localization in (request.localizations or {}).values():
            if not isinstance(localization, dict):
                continue
            title = localization.get("title")
            if title and title != request.title:
                alternate_titles.append(str(title))
        if request.series_title and request.series_title != request.title:
            alternate_titles.append(request.series_title)

        return ReleaseRequestSnapshot(
            id=request.id,
            sonarr_series_id=request.sonarr_series_id,
            title=request.title,
            media_type=request.media_type,
            season_number=request.season_number,
            radarr_movie_id=request.radarr_movie_id,
            year=request.year,
            alternate_titles=alternate_titles,
        )

    def _to_record(self, release: models.Release) -> ReleaseRecord:
        files = [self._to_file_record(file) for file in release.files]
        info_hash = release.info_hash or release.id
        size_bytes = release.size_bytes or 0
        request_ids = [request.id for request in release.requests]
        requests_snapshot = [self._to_request_snapshot(request) for request in release.requests]
        added_at = as_utc(release.added_at) or datetime.now(UTC)
        completed_at = as_utc(release.completed_at)
        torrent_source = release.torrent_source or None
        quality = release.quality or None
        return ReleaseRecord(
            id=release.id,
            name=release.name,
            info_hash=info_hash,
            size_bytes=size_bytes,
            status=release.status,
            progress=release.progress,
            download_speed=release.download_speed,
            upload_speed=release.upload_speed,
            seeders=release.seeders,
            leechers=release.leechers,
            ratio=release.ratio,
            added_at=added_at,
            completed_at=completed_at,
            request_ids=request_ids,
            requests=requests_snapshot,
            torrent_source=torrent_source,
            quality=quality,
            files=files,
            last_exported_info_hash=release.last_exported_info_hash,
            export_failures_count=release.export_failures_count,
            info_url=release.info_url or None,
            published_at=as_utc(release.published_at),
            search_query=release.search_query or None,
            missing_since=as_utc(release.missing_since),
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


__all__ = ["SqlAlchemyReleaseRepository"]
