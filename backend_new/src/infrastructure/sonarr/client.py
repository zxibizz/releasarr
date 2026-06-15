"""HTTP-based Sonarr service implementation."""

from __future__ import annotations

import httpx

from src.application.interfaces.sonarr import (
    MissingSeriesRecord,
    SeriesDetails,
    SeriesSeasonDetails,
    SonarrService,
)


class SonarrHttpClient(SonarrService):
    """Interact with Sonarr's HTTP API."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        timeout_seconds: float = 15.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout_seconds

    async def get_missing_series(self) -> list[MissingSeriesRecord]:
        payload = await self._request(
            "GET",
            "/wanted/missing",
            params={
                "page": 1,
                "pageSize": 1000,
                "includeSeries": "true",
                "includeImages": "false",
                "sortDirection": "descending",
            },
        )

        records: dict[int, MissingSeriesRecord] = {}
        for entry in payload.get("records", []):
            series_info = entry.get("series") or {}
            series_id = int(entry.get("seriesId") or series_info.get("id") or 0)
            if series_id <= 0:
                continue

            record = records.get(series_id)
            if record is None:
                record = MissingSeriesRecord(
                    series_id=series_id,
                    title=str(series_info.get("title") or ""),
                    season_numbers=[],
                    tvdb_id=self._safe_int(series_info.get("tvdbId")),
                    imdb_id=self._safe_str(series_info.get("imdbId")),
                )
                records[series_id] = record

            season_number = int(entry.get("seasonNumber") or 0)
            if season_number not in record.season_numbers:
                record.season_numbers.append(season_number)

        for record in records.values():
            record.season_numbers.sort()

        return list(records.values())

    async def get_series(self, series_id: int) -> SeriesDetails:
        data = await self._request(
            "GET",
            f"/series/{series_id}",
            params={"includeSeasonImages": "false"},
        )

        seasons: dict[int, SeriesSeasonDetails] = {}
        for season_data in data.get("seasons", []):
            season_number = int(season_data.get("seasonNumber") or 0)
            statistics = season_data.get("statistics") or {}
            seasons[season_number] = SeriesSeasonDetails(
                season_number=season_number,
                episode_count=int(statistics.get("episodeCount") or 0),
                total_episode_count=int(
                    statistics.get("totalEpisodeCount") or statistics.get("episodeCount") or 0
                ),
                episode_file_count=int(statistics.get("episodeFileCount") or 0),
            )

        images = data.get("images") or []
        poster_url = self._extract_poster_url(images)

        return SeriesDetails(
            id=int(data.get("id") or series_id),
            title=str(data.get("title") or ""),
            year=self._safe_int(data.get("year")),
            overview=self._safe_str(data.get("overview")),
            poster_url=poster_url,
            imdb_id=self._safe_str(data.get("imdbId")),
            tvdb_id=self._safe_int(data.get("tvdbId")),
            genres=[str(genre) for genre in data.get("genres", []) if genre],
            seasons=seasons,
        )

    async def _request(self, method: str, path: str, **kwargs) -> dict[str, object]:
        headers = {"X-Api-Key": self._api_key}
        timeout = httpx.Timeout(self._timeout)
        async with httpx.AsyncClient(
            base_url=self._base_url,
            headers=headers,
            timeout=timeout,
        ) as client:
            response = await client.request(method, path, **kwargs)
            response.raise_for_status()
            return response.json()

    def _extract_poster_url(self, images: list[dict[str, object]]) -> str | None:
        for image in images:
            if (image.get("coverType") or "").lower() == "poster":
                remote = self._safe_str(image.get("remoteUrl"))
                if remote:
                    return remote
                local = self._safe_str(image.get("url"))
                if local:
                    return local
        return None

    def _safe_int(self, value: object) -> int | None:
        try:
            if value is None:
                return None
            number = int(value)
            return number
        except (TypeError, ValueError):
            return None

    def _safe_str(self, value: object) -> str | None:
        if value is None:
            return None
        result = str(value)
        return result or None


__all__ = ["SonarrHttpClient"]
