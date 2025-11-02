from __future__ import annotations

import asyncio
from datetime import datetime

from loguru import logger
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.clients.factory import get_clients
from app.db.session import AsyncSessionLocal
from app.models import Release, ReleaseFileMatching, Show
from app.schemas.prowlarr import ReleaseData


class OutdatedReleaseRegrabService:
    def __init__(self) -> None:
        self.clients = get_clients()
        self._session_factory = AsyncSessionLocal

    async def run(self) -> None:
        if not (self.clients.prowlarr.enabled and self.clients.qbittorrent.enabled):
            logger.info("Skipping regrab; required clients disabled")
            return

        async with self._session_factory() as session:
            shows = (
                (
                    await session.scalars(
                        select(Show)
                        .where(Show.is_missing.is_(True))
                        .options(
                            selectinload(Show.releases).options(
                                selectinload(Release.file_matchings),
                            )
                        )
                    )
                )
                .unique()
                .all()
            )

        for show in shows:
            await self._process_show(show)

    async def _process_show(self, show: Show) -> None:
        for release in show.releases:
            if not self._release_targets_missing_season(show, release):
                continue
            try:
                await self._try_regrab_release(show, release)
            except Exception:  # pragma: no cover - log only
                logger.exception("Failed to regrab release %s", release.name)

    async def _try_regrab_release(self, show: Show, release: Release) -> None:
        if not release.search and not release.prowlarr_data:
            logger.info("Release %s lacks search metadata", release.name)
            return

        search_query = release.search or release.name
        indexer_ids = None
        if release.prowlarr_data and isinstance(release.prowlarr_data, dict):
            indexer_id = release.prowlarr_data.get(
                "indexerId"
            ) or release.prowlarr_data.get("indexer_id")
            if indexer_id:
                indexer_ids = [indexer_id]

        releases_data = await self.clients.prowlarr.search(
            search_query, indexer_ids=indexer_ids
        )
        target = self._find_release_data(release, releases_data)
        if not target:
            logger.info("No matching release found for %s", release.name)
            return

        torrent_meta, raw_torrent = await self.clients.prowlarr.get_torrent(
            target.download_url
        )
        if (
            release.qbittorrent_guid
            and torrent_meta.info_hash == release.qbittorrent_guid
        ):
            logger.info("Release %s already up to date", release.name)
            return

        await self.clients.qbittorrent.add_torrent(raw_torrent)
        await asyncio.sleep(1)

        torrent_properties = await self.clients.qbittorrent.torrent_properties(
            torrent_meta.info_hash
        )

        async with self._session_factory() as session:
            db_release = await session.get(Release, release.id)
            if not db_release:
                return
            await session.refresh(
                db_release, attribute_names=["file_matchings", "show"]
            )

            db_release.name = torrent_meta.name
            db_release.qbittorrent_guid = torrent_meta.info_hash
            db_release.qbittorrent_data = torrent_properties
            db_release.prowlarr_guid = target.guid
            db_release.prowlarr_data = target.model_dump()
            db_release.updated_at = datetime.utcnow()
            db_release.export_failures_count = 0
            db_release.status = "downloading"
            db_release.progress = 0.0

            self._merge_file_matchings(session, db_release, torrent_meta)

            await session.commit()

    def _find_release_data(
        self, release: Release, releases_data: list[ReleaseData]
    ) -> ReleaseData | None:
        for data in releases_data:
            if release.prowlarr_guid and data.guid == release.prowlarr_guid:
                return data
            if release.name and data.title == release.name:
                return data
        return releases_data[0] if releases_data else None

    def _merge_file_matchings(self, session, release: Release, torrent_meta) -> None:
        existing_names = {matching.file_name for matching in release.file_matchings}
        new_matchings = []
        for file in torrent_meta.files:
            if file.name in existing_names:
                continue
            new_matchings.append(
                ReleaseFileMatching(
                    release_id=release.id,
                    show_id=release.show_id,
                    file_name=file.name,
                )
            )
        if new_matchings:
            session.add_all(new_matchings)

    def _release_targets_missing_season(self, show: Show, release: Release) -> bool:
        if not show.missing_seasons:
            return False
        missing = set(show.missing_seasons)
        for matching in release.file_matchings:
            if matching.season_number in missing:
                return True
        return False
