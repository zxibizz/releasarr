import hashlib
import json
import os

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from src.application.models import Release, Show
from src.db import async_session
from src.infrastructure.api_clients.prowlarr import ProwlarrApiClient
from src.infrastructure.api_clients.sonarr import (
    SonarrApiClient,
    SonarrImportFile,
)
from src.infrastructure.api_clients.tvdb import TVDBApiClient


class ShowService:
    def __init__(self) -> None:
        self.sonarr_api_client = SonarrApiClient()
        self.tvdb_api_client = TVDBApiClient()
        self.prowlarr_api_client = ProwlarrApiClient()

    async def get_missing(self) -> list[Show]:
        async with async_session() as session, session.begin():
            return await session.scalars(select(Show).where(Show.is_missing))

    async def get_all(self) -> list[Show]:
        async with async_session() as session, session.begin():
            return await session.scalars(select(Show))

    async def get_show(self, show_id: int) -> Show:
        async with async_session() as session, session.begin():
            return await session.scalar(
                select(Show)
                .where(Show.id == show_id)
                .options(
                    joinedload(Show.releases).options(
                        joinedload(Release.file_matchings)
                    ),
                )
            )

    async def sync_show_release_files(self, show_id: int):
        async with async_session() as session, session.begin():
            show = await self.get_show(show_id)
            for release in show.releases:
                import_files = []
                torrent_data = json.loads(release.qbittorrent_data)
                for file_matching in release.file_matchings:
                    episode_id = None
                    for season in show.sonarr_data.seasons:
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
                                series_id=show.sonarr_id,
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

            await session.commit()

    async def get_outdated_releases(self) -> list[Release]:
        missing_shows = await self.get_missing()
        res = []
        for missing_show in missing_shows:
            show = await self.get_show(missing_show.id)
            for release in show.releases:
                for matching in release.file_matchings:
                    if matching.season_number in show.missing_seasons:
                        res.append(release)
                        break

        return res
