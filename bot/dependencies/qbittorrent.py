import asyncio
import os

import httpx


class _Auth(httpx.Auth):
    def __init__(self, base_url) -> None:
        self.base_url = base_url

    # async def async_auth_flow(self, request):
    #     if self.auth_token is None:
    #         async with self._async_lock:
    #             self.auth_token = os.environ.get("TVDB_API_AUTH_TOKEN")
    #             # res: httpx.Response = yield self.build_refresh_request()
    #             # res.raise_for_status()
    #             # await res.aread()
    #             # self.auth_token = res.json()["data"]["token"]

    #     request.headers["Authorization"] = f"Bearer {self.auth_token}"
    #     yield request

    # def build_refresh_request(self) -> httpx.Request:
    #     return httpx.Request(
    #         method="POST", url=self.base_url + "/login", json={"apiKey": self.api_token}
    #     )


class QBittorrentApiClient:
    def __init__(self) -> None:
        self.base_url = os.environ.get("QBITTORRENT_BASE_URL")
        self.client = httpx.AsyncClient(
            base_url=self.base_url,  # auth=_Auth(base_url=self.base_url)
        )

    async def log_in(self):
        res = await self.client.post(
            "/auth/login",
            data={
                "username": os.environ.get("QBITTORRENT_USERNAME"),
                "password": os.environ.get("QBITTORRENT_PASSWORD"),
            },
        )
        print(res)

    async def torrent_properties(self, hash):
        res = await self.client.get("/torrents/properties", params={"hash": hash})
        print(res)


if __name__ == "__main__":
    client = QBittorrentApiClient()

    async def _main():
        await client.log_in()
        await client.torrent_properties("1893e0a4728658ce3be236e03f7a6dd356e5279b")

    asyncio.run(_main())
