import asyncio
import json
from datetime import datetime

from src.application.interfaces.db_manager import I_DBManager
from src.application.interfaces.release_searcher import I_ReleaseSearcher
from src.application.interfaces.releases_repository import I_ReleasesRepository
from src.application.interfaces.torrent_client import I_TorrentClient
from src.application.models import Release, ReleaseFileMatching
from src.application.schemas import ReleaseData, TorrentMeta
from src.application.utility.release_files_matchings_autocompleter import (
    ReleaseFileMatchingsAutocompleter,
)


class UseCase_ReGrabOutdatedReleases:
    def __init__(
        self,
        db_manager: I_DBManager,
        release_searcher: I_ReleaseSearcher,
        torrent_client: I_TorrentClient,
        releases_repository: I_ReleasesRepository,
        release_files_matching_autocompleter: ReleaseFileMatchingsAutocompleter,
    ) -> None:
        self.db_manager = db_manager
        self.release_searcher = release_searcher
        self.torrent_client = torrent_client
        self.releases_repository = releases_repository
        self.release_files_matching_autocompleter = release_files_matching_autocompleter

    async def process(self):
        async with self.db_manager.begin_session() as db_session:
            outdated_releases = await self.releases_repository.get_outdated_releases(
                db_session=db_session
            )

        for release in outdated_releases:
            found_releases_data = await self.release_searcher.search(release.search)
            current_release_data = self._find_release_data(
                release=release, releases_data=found_releases_data
            )
            if current_release_data is None:
                print("Achtung! Couldn't find the release!")
                continue

            new_torrent_meta, raw_torrent = await self.release_searcher.get_torrent(
                current_release_data.download_url
            )

            # TODO: Perform this check without downloading the torrent. Mb we can
            # save the release data and then compare it instead of the infohash.
            # Do not try to use the infohash from `current_release_data` as it is
            # not always provided by prowlarr
            if new_torrent_meta.info_hash == release.qbittorrent_guid:
                continue

            file_matchings = self._add_new_file_matchings(
                release=release, new_torrent_meta=new_torrent_meta
            )

            await self.torrent_client.add_torrent(raw_torrent)
            await asyncio.sleep(1)
            new_torrent_data = await self.torrent_client.torrent_properties(
                new_torrent_meta.info_hash
            )

            async with self.db_manager.begin_session() as db_session:
                release.name = new_torrent_data["name"]
                release.updated_at = datetime.now()
                release.qbittorrent_guid = new_torrent_meta.info_hash
                release.qbittorrent_data = json.dumps(new_torrent_data)

                await self.releases_repository.update(
                    db_session=db_session, release=release
                )
                await self.releases_repository.update_file_matchings(
                    db_session=db_session, file_matchings=file_matchings
                )

    @staticmethod
    def _find_release_data(
        release: Release, releases_data: list[ReleaseData]
    ) -> ReleaseData | None:
        for release_data in releases_data:
            if release_data.pk == release.prowlarr_data.pk:
                return release_data

    def _add_new_file_matchings(self, release: Release, new_torrent_meta: TorrentMeta):
        file_matchings = list(release.file_matchings)
        existing_file_names = {f.file_name for f in file_matchings}

        new_files_count = 0
        for file in new_torrent_meta.files:
            if file.name not in existing_file_names:
                file_matchings.append(
                    {
                        ReleaseFileMatching.release_name: new_torrent_meta.name,
                        ReleaseFileMatching.show_id: release.show_id,
                        ReleaseFileMatching.file_name: file.name,
                    }
                )
                new_files_count += 1

        if not new_files_count:
            print("No new files in the updated release!")

        self.release_files_matching_autocompleter.autocomplete(file_matchings)

        return file_matchings
