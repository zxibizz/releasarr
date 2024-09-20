import json
from src.application.interfaces import releases_repository


class UseCase_UploadFinishedSeries:
    async def process(self):
        
    # TODO: extract to a different UseCase
    async def _sync_show_releases(self, show: Show) -> None:
        finished_not_uploaded_releases = async self.releases_repository.get_finished_not_uploaded()
        for release in finished_not_uploaded_releases:
            import_files = []
            torrent_data = json.loads(release.qbittorrent_data)
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
                        SonarrImportFile(
                            episode_ids=[episode_id],
                            folder_name=torrent_data["name"],
                            path=os.path.join(
                                torrent_data["save_path"],
                                file_matching.file_name,
                            ),
                            series_id=release.show.sonarr_id,
                        )
                    )
            if import_files:
                import_files_hash = hashlib.sha256(
                    str(import_files).encode()
                ).hexdigest()
                if release.last_imported_files_hash != import_files_hash:
                    await self.sonarr_api_client.manual_import(import_files)
                    release.last_imported_files_hash = import_files_hash
                    session.add(release)
