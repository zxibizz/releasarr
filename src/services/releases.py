import json
import os
from datetime import datetime

from sqlalchemy import insert, select, update
from sqlalchemy.orm import joinedload

from src.db import async_session
from src.deps.prowlarr import ProwlarrApiClient
from src.deps.qbittorrent import QBittorrentApiClient
from src.models import Release, ReleaseFileMatching


class ReleasesService:
    def __init__(self):
        self.qbittorrent_client = QBittorrentApiClient()
        self.prowlarr_client = ProwlarrApiClient()

    async def grab(
        self, show_id: int, search: str, prowlarr_guid: str, download_url: str
    ):
        await self.qbittorrent_client.log_in()
        meta, torrent = await self.prowlarr_client.get_torrent(download_url)
        await self.qbittorrent_client.add_torrent(torrent)
        torrent_data = await self.qbittorrent_client.torrent_properties(meta.info_hash)

        async with async_session() as session, session.begin():
            await session.execute(
                insert(Release).values(
                    {
                        Release.name: torrent_data["name"],
                        Release.updated_at: datetime.now(),
                        Release.search: search,
                        Release.prowlarr_guid: prowlarr_guid,
                        Release.show_id: show_id,
                        Release.qbittorrent_guid: meta.info_hash,
                        Release.qbittorrent_data: json.dumps(torrent_data),
                    }
                )
            )
            await session.execute(
                insert(ReleaseFileMatching).values(
                    [
                        {
                            ReleaseFileMatching.release_name: torrent_data["name"],
                            ReleaseFileMatching.show_id: show_id,
                            ReleaseFileMatching.file_name: file.name,
                        }
                        for file in meta.files
                    ]
                )
            )

    async def re_grab(self, release_name: int):
        async with async_session() as session, session.begin():
            release: Release = await session.scalar(
                select(Release)
                .filter(Release.name == release_name)
                .options(joinedload(Release.file_matchings))
            )

            prowlarr_releases = await self.prowlarr_client.search(release.search)
            current_prowlarr_release = None

            for prowlarr_release in prowlarr_releases:
                if prowlarr_release.guid == release.prowlarr_guid:
                    current_prowlarr_release = prowlarr_release
                    break

            if not current_prowlarr_release:
                return

            meta, torrent = await self.prowlarr_client.get_torrent(
                current_prowlarr_release.download_url
            )
            if meta.info_hash == release.qbittorrent_guid:
                return

            await self.qbittorrent_client.log_in()
            await self.qbittorrent_client.add_torrent(torrent)
            torrent_data = await self.qbittorrent_client.torrent_properties(
                meta.info_hash
            )

            await session.execute(
                update(Release)
                .where(Release.name == release_name)
                .values(
                    {
                        Release.name: torrent_data["name"],
                        Release.updated_at: datetime.now(),
                        Release.qbittorrent_guid: meta.info_hash,
                        Release.qbittorrent_data: json.dumps(torrent_data),
                    }
                )
            )

            existing_files = {f.file_name: f for f in release.file_matchings}
            new_files = []
            prev_season = None
            prev_episode = None
            prev_dir = None
            for file in meta.files:
                if file.name in existing_files:
                    prev_season = existing_files[file.name].season_number
                    prev_episode = existing_files[file.name].episode_number
                else:
                    if prev_dir is not None and prev_dir != os.path.dirname(file.name):
                        prev_season = None
                        prev_episode = None

                    if prev_episode is not None:
                        prev_episode += 1

                    new_files.append(
                        {
                            ReleaseFileMatching.release_name: torrent_data["name"],
                            ReleaseFileMatching.show_id: release.show_id,
                            ReleaseFileMatching.file_name: file.name,
                            ReleaseFileMatching.season_number: prev_season,
                            ReleaseFileMatching.episode_number: prev_episode,
                        }
                    )

                prev_dir = os.path.dirname(file.name)

            await session.execute(insert(ReleaseFileMatching).values(new_files))

    async def update_file_matching(
        self, release_name: str, new_file_matching: list[dict]
    ):
        async with async_session() as session, session.begin():
            for m in new_file_matching:
                await session.execute(
                    update(ReleaseFileMatching)
                    .values(
                        {
                            ReleaseFileMatching.season_number: m["season_number"],
                            ReleaseFileMatching.episode_number: m["episode_number"],
                        }
                    )
                    .where(
                        ReleaseFileMatching.release_name == release_name,
                        ReleaseFileMatching.file_name == m["file_name"],
                    )
                )

    async def get_shows_having_finished_releases(self):
        await self.qbittorrent_client.log_in()
        stats = await self.qbittorrent_client.get_stats()
        finished_torrents = [
            t.infohash_v1
            for t in stats.torrents.values()
            if t.seen_complete is not None
        ]

        async with async_session() as session, session.begin():
            return list(
                await session.scalars(
                    select(Release.show_id).where(
                        Release.qbittorrent_guid.in_(finished_torrents)
                    )
                )
            )
