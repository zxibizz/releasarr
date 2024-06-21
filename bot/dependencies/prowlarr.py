import os
from datetime import datetime

import httpx
from pydantic import BaseModel
from torrentool.api import Torrent


class ProwlarrRelease(BaseModel):
    guid: str
    age: int
    grabs: int
    info_url: str
    size: int
    title: str
    indexer: str
    seeders: int
    leechers: int
    download_url: str


class ProwlarrTorrent(BaseModel):
    name: str
    content: bytes
    info_hash: str
    total_size: int
    creation_date: datetime
    files: list["ProwlarrTorrentFile"]


class ProwlarrTorrentFile(BaseModel):
    name: str
    length: int


class ProwlarrApiClient:
    def __init__(self) -> None:
        self.base_url = os.environ.get("PROWLARR_BASE_URL")
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={"X-Api-Key": os.environ.get("PROWLARR_API_TOKEN")},
        )

    async def search(self, query: str) -> list[ProwlarrRelease]:
        res = await self.client.get(
            "/search", params={"query": query, "type": "search"}, timeout=60
        )
        releases_data = res.json()
        result = []

        for release_data in releases_data:
            result.append(
                ProwlarrRelease(
                    guid=release_data["guid"],
                    age=release_data["age"],
                    grabs=release_data.get("grabs", 0),
                    info_url=release_data["infoUrl"],
                    size=release_data["size"],
                    title=release_data["title"],
                    indexer=release_data["indexer"],
                    seeders=release_data["seeders"],
                    leechers=release_data["leechers"],
                    download_url=release_data["downloadUrl"],
                )
            )
        result = sorted(result, key=lambda release: release.age)
        return result

    async def get_torrent(self, download_url) -> ProwlarrTorrent:
        res = await self.client.get(download_url)
        t = Torrent.from_string(res.content)
        return ProwlarrTorrent(
            name=t.name,
            content=res.content,
            info_hash=t.info_hash,
            total_size=t.total_size,
            creation_date=t.creation_date,
            files=[ProwlarrTorrentFile(name=f.name, length=f.length) for f in t.files],
        )


if __name__ == "__main__":
    import asyncio

    client = ProwlarrApiClient()
    asyncio.run(
        client.get_torrent(
            "https://prowlarr.koreetz.synology.me/1/download?apikey=53c61e4ae06c4a3aaf7e20dfd2954331&link=cUNPRkhMSnpFTlFPOU11VmNDaTl3VW01dC94UFV0aVE3d3FxTHBmSzlndjRncU9RVmxnaFVvRllnb3I3Z3d2MWZSTllBdUdwdXBINHQ1WDdxU3ZyQnlPMHlNVlJIc0pBMWF6M09aWWVCNzA9&file=%D0%9C%D0%B5%D0%B4%D1%83%D0%B7%D0%B0+%D0%BD%D0%B5+%D1%83%D0%BC%D0%B5%D0%B5%D1%82+%D0%BF%D0%BB%D0%B0%D0%B2%D0%B0%D1%82%D1%8C+%D0%B2+%D0%BD%D0%BE%D1%87%D0%B8+%2F+Yoru+no+Kurage+wa+Oyogenai+S1E1-10+%5BWEBRip+1080p+x265%5D"
        )
    )
