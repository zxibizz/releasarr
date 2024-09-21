import json
import os

from src.application.interfaces.db_manager import I_DBManager
from src.application.interfaces.releases_repository import I_ReleasesRepository
from src.application.interfaces.series_service import I_SeriesService, SeriesImportFile
from src.application.models import Release
from src.application.schemas import TorrentFile


class UseCase_ExportFinishedSeries:
    def __init__(
        self,
        db_manager: I_DBManager,
        releases_repository: I_ReleasesRepository,
        series_service: I_SeriesService,
    ) -> None:
        self.db_manager = db_manager
        self.releases_repository = releases_repository
        self.series_service = series_service

    async def process(self):
        async with self.db_manager.begin_session() as db_session:
            finished_not_uploaded_releases = (
                await self.releases_repository.get_finished_not_uploaded(
                    db_session=db_session
                )
            )

        for release in finished_not_uploaded_releases:
            import_files = self._get_import_files(release)
            if not import_files:
                print("No files to import =(")
                continue

            await self.series_service.manual_import(import_files)
            release.last_exported_torrent_guid = release.qbittorrent_guid

            async with self.db_manager.begin_session() as db_session:
                await self.releases_repository.update(
                    db_session=db_session, release=release
                )

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
