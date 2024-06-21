import os

import httpx
from pydantic import BaseModel


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
                )
            )
        result = sorted(result, key=lambda release: release.age)
        return result


if __name__ == "__main__":
    import asyncio

    client = ProwlarrApiClient()
    asyncio.run(client.search("Твое имя"))
