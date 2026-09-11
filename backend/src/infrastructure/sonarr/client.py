"""HTTP-based Sonarr service implementation."""

from __future__ import annotations

from typing import Any

import httpx

from src.application.interfaces.sonarr import (
    ManualImportFile,
    MissingSeriesRecord,
    SeriesDetails,
    SeriesSeasonDetails,
    SonarrEpisode,
    SonarrService,
)
from src.infrastructure.http import BaseHttpClient, HttpClientError


class SonarrHttpClient(SonarrService):
    """Interact with Sonarr's HTTP API."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        timeout_seconds: float = 15.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._http = BaseHttpClient(
            base_url=base_url,
            headers={"X-Api-Key": api_key},
            timeout=timeout_seconds,
            transport=transport,
        )

    async def aclose(self) -> None:
        await self._http.aclose()

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

    async def get_episodes(self, series_id: int) -> list[SonarrEpisode]:
        data = await self._request("GET", "/episode", params={"seriesId": series_id})
        if not isinstance(data, list):
            return []

        episodes = []
        for item in data:
            episodes.append(
                SonarrEpisode(
                    id=int(item.get("id") or 0),
                    season_number=int(item.get("seasonNumber") or 0),
                    episode_number=int(item.get("episodeNumber") or 0),
                )
            )
        return episodes

    async def manual_import(self, files: list[ManualImportFile]) -> bool:
        if not files:
            return True

        command_files = [
            {
                "path": file.path,
                "seriesId": file.series_id,
                "episodeIds": file.episode_ids,
                "folderName": file.folder_name,
            }
            for file in files
        ]

        try:
            await self._request(
                "POST",
                "/command",
                json={
                    "name": "ManualImport",
                    "files": command_files,
                    "importMode": "Auto",
                },
            )
            return True
        except (HttpClientError, httpx.HTTPError):
            return False

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        return await self._http.request_json(method, path, **kwargs)

    def _extract_poster_url(self, images: list[dict[str, object]]) -> str | None:
        for image in images:
            if str(image.get("coverType") or "").lower() == "poster":
                remote = self._safe_str(image.get("remoteUrl"))
                if remote:
                    return remote
                local = self._safe_str(image.get("url"))
                if local:
                    return local
        return None

    def _safe_int(self, value: object) -> int | None:
        if not isinstance(value, int | float | str):
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _safe_str(self, value: object) -> str | None:
        if value is None:
            return None
        result = str(value)
        return result or None


__all__ = ["SonarrHttpClient"]
