from __future__ import annotations

import os
from datetime import datetime

from loguru import logger
from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload

from app.clients.factory import get_clients
from app.clients.sonarr import SeriesManualImportError
from app.db.session import AsyncSessionLocal
from app.models import Release
from app.schemas.sonarr import Series, SeriesImportFile


class FinishedReleaseExportService:
    def __init__(self) -> None:
        self.clients = get_clients()
        self._session_factory = AsyncSessionLocal

    async def run(self) -> None:
        if not self.clients.sonarr.enabled:
            logger.info("Skipping release export; Sonarr disabled")
            return

        async with self._session_factory() as session:
            releases = (
                (
                    await session.scalars(
                        select(Release)
                        .where(Release.torrent_is_finished.is_(True))
                        .where(
                            or_(
                                Release.last_exported_torrent_guid.is_(None),
                                Release.last_exported_torrent_guid
                                != Release.qbittorrent_guid,
                            )
                        )
                        .where(Release.export_failures_count < 5)
                        .options(
                            selectinload(Release.file_matchings),
                            selectinload(Release.show),
                        )
                    )
                )
                .unique()
                .all()
            )

            for release in releases:
                await self._process_release(session, release)

            await session.commit()

    async def _process_release(self, session, release: Release) -> None:
        if not release.show or not release.file_matchings:
            logger.info("Release %s missing show or file matchings", release.name)
            return

        if not release.qbittorrent_data:
            logger.info("Release %s lacks torrent metadata", release.name)
            return

        try:
            sonarr_series = Series.model_validate(release.show.sonarr_data)
        except Exception:
            logger.warning("Invalid Sonarr data for show %s", release.show.id)
            return

        import_files = self._build_import_files(release, sonarr_series)
        if not import_files:
            logger.info("No import files derived for release %s", release.name)
            return

        try:
            await self.clients.sonarr.manual_import(import_files)
        except SeriesManualImportError:
            release.export_failures_count += 1
            logger.warning("Manual import failed for %s", release.name)
            return

        release.last_exported_torrent_guid = release.qbittorrent_guid
        release.export_failures_count = 0
        release.completed_date = release.completed_date or datetime.utcnow()

    def _build_import_files(
        self, release: Release, series: Series
    ) -> list[SeriesImportFile]:
        files = []
        torrent_name = (
            release.qbittorrent_data.get("name")
            if isinstance(release.qbittorrent_data, dict)
            else None
        )
        save_path = (
            release.qbittorrent_data.get("content_path")
            if isinstance(release.qbittorrent_data, dict)
            else None
        )
        if not torrent_name or not save_path:
            return []

        episode_lookup = {}
        for season in series.seasons:
            episode_lookup.setdefault(season.season_number, {})
            for episode in season.episodes:
                episode_lookup[season.season_number][episode.episode_number] = (
                    episode.id
                )

        for matching in release.file_matchings:
            if matching.season_number is None or matching.episode_number is None:
                continue
            episode_id = episode_lookup.get(matching.season_number, {}).get(
                matching.episode_number
            )
            if not episode_id:
                continue
            file_path = os.path.join(save_path, matching.file_name)
            files.append(
                SeriesImportFile(
                    episode_ids=[episode_id],
                    folder_name=torrent_name,
                    path=file_path,
                    series_id=series.id,
                )
            )
        return files
