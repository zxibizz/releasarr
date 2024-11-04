import os
from typing import Optional

import httpx
from torrentool.api import Torrent

from src.application.interfaces.release_searcher import (
    I_ReleaseSearcher,
    NoIndexerAvailableError,
    SearchError,
)
from src.application.schemas import ReleaseData, TorrentFile, TorrentMeta


class ProwlarrApiClient(I_ReleaseSearcher):
    def __init__(self) -> None:
        self.base_url = os.environ.get("PROWLARR_BASE_URL")
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={"X-Api-Key": os.environ.get("PROWLARR_API_TOKEN")},
        )

    async def search(
        self, search_string: str, indexer_ids: Optional[list[int]] = None
    ) -> list[ReleaseData]:
        params = [("query", search_string), ("type", "search")]

        for indexer_id in indexer_ids or []:
            params.append(("indexerIds", indexer_id))

        res = await self.client.get("/search", params=params, timeout=60)
        releases_data = res.json()
        if res.status_code == 400:
            if (
                releases_data["message"]
                == "Search failed due to all selected indexers being unavailable"
            ):
                raise NoIndexerAvailableError
            raise SearchError
        result: list[ReleaseData] = []

        for release_data in releases_data:
            if "downloadUrl" not in release_data:
                continue
            result.append(
                ReleaseData(
                    guid=release_data["guid"],
                    age=release_data["age"],
                    grabs=release_data.get("grabs", 0),
                    info_url=release_data["infoUrl"],
                    size=release_data["size"],
                    title=release_data["title"],
                    indexer=release_data["indexer"],
                    indexer_id=release_data["indexerId"],
                    seeders=release_data["seeders"],
                    leechers=release_data["leechers"],
                    download_url=release_data["downloadUrl"],
                )
            )
        result = sorted(result, key=lambda release: release.age)
        return result

    async def get_torrent(self, download_url) -> tuple[TorrentMeta, bytes]:
        res = await self.client.get(download_url, timeout=60)
        t = Torrent.from_string(res.content)
        return TorrentMeta(
            name=t.name,
            info_hash=t.info_hash,
            total_size=t.total_size,
            creation_date=t.creation_date,
            files=[TorrentFile(name=f.name, length=f.length) for f in t.files],
        ), res.content
