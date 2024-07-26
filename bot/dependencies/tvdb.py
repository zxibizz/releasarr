import asyncio
import os
from dataclasses import dataclass

import httpx


@dataclass
class TVDBShow:
    id: int
    year: int
    genres: str
    country: str
    title: str
    image_url: str | None
    overview: str


class _Auth(httpx.Auth):
    def __init__(self, base_url) -> None:
        self.api_token = os.environ.get("TVDB_API_TOKEN")
        self.base_url = base_url
        self.auth_token = None
        self._async_lock = asyncio.Lock()

    async def get_auth_token(self) -> str:
        res = await self.client.post("/login", json={"apiKey": self.api_token})
        res.raise_for_status()
        return res.json()["data"]["token"]

    async def async_auth_flow(self, request):
        if self.auth_token is None:
            async with self._async_lock:
                self.auth_token = os.environ.get("TVDB_API_AUTH_TOKEN")
                # res: httpx.Response = yield self.build_refresh_request()
                # res.raise_for_status()
                # await res.aread()
                # self.auth_token = res.json()["data"]["token"]

        request.headers["Authorization"] = f"Bearer {self.auth_token}"
        yield request

    def build_refresh_request(self) -> httpx.Request:
        return httpx.Request(
            method="POST", url=self.base_url + "/login", json={"apiKey": self.api_token}
        )


class TVDBApiClient:
    def __init__(self) -> None:
        self.base_url = "https://api4.thetvdb.com/v4"
        self.client = httpx.AsyncClient(
            base_url=self.base_url, auth=_Auth(base_url=self.base_url)
        )

    async def search(self, query: str):
        res = await self.client.get("/search", params={"query": query})
        data = res.json()["data"]
        result = []
        for show in data:
            if show["type"] not in ["movie", "series"]:
                continue
            result.append(
                {
                    "id": show["tvdb_id"],
                    "type": show["type"],
                    "year": show.get("year"),
                    "genres": show.get("genres") or [],
                    "country": show.get("country"),
                    "title": show["name"],
                    "title_eng": show["translations"].get("eng"),
                    "title_rus": show["translations"].get("rus"),
                    "image_url": show.get("thumbnail"),
                    "overview": show.get("overview"),
                    "overview_eng": show.get("overviews", {}).get("eng"),
                    "overview_rus": show.get("overviews", {}).get("rus"),
                }
            )
        return result

    async def get_series(self, series_id: int):
        res = await self.client.get(
            f"/series/{series_id}/extended", params={"meta": "translations"}
        )
        show_data = res.json()["data"]
        return await self._get_show(show_data)

    async def _get_show(self, show_data: dict) -> TVDBShow:
        return TVDBShow(
            id=show_data["id"],
            year=show_data.get("year"),
            genres=show_data.get("genres") or [],
            country=show_data.get("originalCountry"),
            title=self._extract_show_name(show_data),
            image_url=show_data.get("image"),
            overview=self._extract_show_overview(show_data),
        )

    @staticmethod
    def _extract_show_name(show_data: dict):
        name_rus = None
        name_eng = None
        name_original = show_data["name"]
        for name_translation_data in show_data.get("translations", {}).get(
            "nameTranslations"
        ):
            if name_translation_data["language"] == "rus" and not name_rus:
                name_rus = name_translation_data["name"]
            if name_translation_data["language"] == "eng" and not name_eng:
                name_eng = name_translation_data["name"]
        return name_rus or name_eng or name_original

    @staticmethod
    def _extract_show_overview(show_data: dict):
        overview_rus = None
        overview_eng = None
        overview_original = show_data["overview"]
        for overview_translation_data in show_data.get("translations", {}).get(
            "overviewTranslations"
        ):
            if overview_translation_data["language"] == "rus" and not overview_rus:
                overview_rus = overview_translation_data["overview"]
            if overview_translation_data["language"] == "eng" and not overview_eng:
                overview_eng = overview_translation_data["overview"]
        return overview_rus or overview_eng or overview_original
