from __future__ import annotations

import json
import os

import loguru

from src.application.interfaces.db_manager import I_DBManager
from src.application.interfaces.releases_repository import I_ReleasesRepository
from src.application.interfaces.series_service import I_SeriesService, SeriesImportFile
from src.application.models import Release
from src.application.schemas import TorrentFile
from src.infrastructure.api_clients.sonarr import E_SeriesManualImportError


class DTO_ExportFinishedSeriesResult:
    succeded: int = 0
    failed: int = 0


class UseCase_ExportFinishedSeries:
    def __init__(
        self,
        db_manager: I_DBManager,
        releases_repository: I_ReleasesRepository,
        series_service: I_SeriesService,
        logger: loguru.Logger,
    ) -> DTO_ExportFinishedSeriesResult:
        self.db_manager = db_manager
        self.releases_repository = releases_repository
        self.series_service = series_service
        self.logger = logger

    async def process(self):
        self.logger.info("Exporting finished series")
        with self.logger.catch(reraise=True):
            return await self._process()

    async def _process(self):
        async with self.db_manager.begin_session() as db_session:
            finished_not_uploaded_releases = (
                await self.releases_repository.get_finished_not_uploaded(
                    db_session=db_session
                )
            )
        res = DTO_ExportFinishedSeriesResult()

        for release in finished_not_uploaded_releases:
            import_files = self._get_import_files(release)
            if not import_files:
                self.logger.info("No files to import")
                continue

            try:
                await self.series_service.manual_import(import_files)

                # TODO: add a check of the import result. Sometime it happens
                # that there are an issues occured during the import and in that
                # cases we shouldn't update the `last_exported_torrent_guid`
                # Also we should keep track of the failed imports not to try
                # to import a buggy release infinitely
                release.last_exported_torrent_guid = release.qbittorrent_guid

                res.succeded += 1

            except E_SeriesManualImportError:
                release.export_failures_count += 1
                res.failed += 1

            async with self.db_manager.begin_session() as db_session:
                # TODO: Concurrent update may occur here as this is a new transaction
                await self.releases_repository.update(
                    db_session=db_session, release=release
                )

        return res

    @staticmethod
    def _get_import_files(release: Release) -> list[SeriesImportFile]:
        import_files = []
        torrent_data: TorrentFile = json.loads(release.qbittorrent_data)
        for file_matching in release.file_matchings:
            episode_id = None
            for season in release.show.sonarr_data.seasons:
                if season.season_number != file_matching.season_number:
                    continue
                for episode in season.episodes:
                    if episode.episode_number == file_matching.episode_number:
                        episode_id = episode.id
            if episode_id is not None:
                import_files.append(
                    SeriesImportFile(
                        episode_ids=[episode_id],
                        folder_name=torrent_data["name"],
                        path=os.path.join(
                            torrent_data["save_path"],
                            file_matching.file_name,
                        ),
                        series_id=release.show.sonarr_id,
                    )
                )
        return import_files
