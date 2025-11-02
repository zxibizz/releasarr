from __future__ import annotations

from http import HTTPStatus
from typing import Any, Iterable

import httpx
from loguru import logger

from app.core.config import Settings
from app.schemas.sonarr import (
    Episode,
    MissingSeries,
    Season,
    Series,
    SeriesImportFile,
)


class SeriesManualImportError(Exception):
    """Raised when Sonarr manual import fails."""


class SonarrClient:
    """Thin async wrapper around the Sonarr API used for series orchestration."""

    def __init__(self, settings: Settings) -> None:
        self._enabled = not settings.mock_external_services and bool(
            settings.sonarr_url and settings.sonarr_api_key
        )
        self._base_url = settings.sonarr_url
        self._api_key = settings.sonarr_api_key
        self._client: httpx.AsyncClient | None = None

    @property
    def enabled(self) -> bool:
        return self._enabled

    async def _get_client(self) -> httpx.AsyncClient:
        if not self.enabled:
            raise RuntimeError("Sonarr client is not configured")
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=str(self._base_url),
                headers={"X-Api-Key": str(self._api_key)},
                timeout=60,
            )
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def ensure_series(
        self,
        tvdb_id: int,
        title: str,
        quality_profile_id: int = 1,
        language_profile_id: int = 1,
        root_folder_path: str = "/data/series",
    ) -> dict[str, Any] | None:
        """
        Creates the series in Sonarr if it does not exist yet.
        Returns the Sonarr series payload or ``None`` when client is disabled.
        """

        if not self.enabled:
            logger.info("Skipping Sonarr ensure_series; client disabled")
            return None

        client = await self._get_client()
        logger.info("Ensuring Sonarr has series for %s", title)
        payload = {
            "tvdbId": tvdb_id,
            "title": title,
            "qualityProfileId": quality_profile_id,
            "languageProfileId": language_profile_id,
            "rootFolderPath": root_folder_path,
            "seasonFolder": True,
            "monitored": True,
            "tags": [],
            "addOptions": {
                "monitor": "all",
                "searchForMissingEpisodes": False,
            },
        }
        response = await client.post("/api/v3/series", json=payload)
        if response.status_code in (HTTPStatus.OK, HTTPStatus.CREATED):
            return response.json()

        if response.status_code == HTTPStatus.CONFLICT:
            # Already exists, fetch current state
            logger.info("Series already exists in Sonarr, fetching current metadata")
            lookup = await client.get("/api/v3/series", params={"tvdbId": tvdb_id})
            lookup.raise_for_status()
            data = lookup.json()
            if isinstance(data, list) and data:
                return data[0]
            return None

        logger.warning(
            "Sonarr ensure_series failed with status %s: %s",
            response.status_code,
            response.text,
        )
        response.raise_for_status()
        return None

    async def get_missing(self) -> list[MissingSeries]:
        if not self.enabled:
            logger.info("Skipping Sonarr get_missing; client disabled")
            return []

        client = await self._get_client()
        response = await client.get(
            "/api/v3/wanted/missing",
            params={
                "page": 1,
                "pageSize": 1000,
                "includeSeries": "true",
                "includeImages": "false",
                "monitored": "true",
            },
        )
        response.raise_for_status()
        records = response.json().get("records", [])
        series_map: dict[int, MissingSeries] = {}

        for row in records:
            series_id = row.get("seriesId")
            if series_id is None:
                continue
            tvdb_id = row.get("series", {}).get("tvdbId")
            season_number = row.get("seasonNumber")
            missing = series_map.get(series_id)
            if not missing:
                missing = MissingSeries(
                    id=series_id,
                    tvdb_id=tvdb_id or 0,
                    season_numbers=[season_number] if season_number is not None else [],
                )
                series_map[series_id] = missing
            else:
                if (
                    season_number is not None
                    and season_number not in missing.season_numbers
                ):
                    missing.season_numbers.append(season_number)

        for missing in series_map.values():
            missing.season_numbers.sort()

        return list(series_map.values())

    async def get_series(self, series_id: int) -> Series:
        if not self.enabled:
            raise RuntimeError("Sonarr client disabled")

        client = await self._get_client()
        response = await client.get(
            f"/api/v3/series/{series_id}",
            params={"includeSeasonImages": "false"},
        )
        response.raise_for_status()
        payload = response.json()

        seasons: list[Season] = []
        for season in payload.get("seasons", []):
            season_number = season.get("seasonNumber")
            episodes_resp = await client.get(
                "/api/v3/episode",
                params={
                    "seriesId": series_id,
                    "seasonNumber": season_number,
                },
            )
            episodes_resp.raise_for_status()
            episodes = [
                Episode(
                    id=episode.get("id"),
                    episode_number=episode.get("episodeNumber"),
                )
                for episode in episodes_resp.json()
            ]
            seasons.append(
                Season(
                    season_number=season_number,
                    episode_file_count=season.get("statistics", {}).get(
                        "episodeFileCount", 0
                    ),
                    episode_count=season.get("statistics", {}).get("episodeCount", 0),
                    episodes=episodes,
                    total_episodes_count=season.get("statistics", {}).get(
                        "totalEpisodeCount", 0
                    ),
                    previous_airing=season.get("statistics", {}).get("previousAiring"),
                )
            )

        return Series(
            id=payload.get("id"),
            path=payload.get("path"),
            tvdb_id=payload.get("tvdbId"),
            seasons=seasons,
        )

    async def manual_import(self, import_files: Iterable[SeriesImportFile]) -> None:
        if not self.enabled:
            logger.info("Skipping Sonarr manual_import; client disabled")
            return

        files_payload = [
            {
                "episodeIds": item.episode_ids,
                "indexerFlags": item.indexer_flags,
                "languages": [{"id": 1, "name": "English"}],
                "path": item.path,
                "quality": {
                    "quality": {
                        "id": 9,
                        "name": "HDTV-1080p",
                        "source": "television",
                        "resolution": 1080,
                    },
                    "revision": {"version": 1, "real": 0, "isRepack": False},
                },
                "releaseType": item.release_type,
                "seriesId": item.series_id,
            }
            for item in import_files
        ]

        if not files_payload:
            return

        client = await self._get_client()

        check_response = await client.post("/api/v3/manualimport", json=files_payload)
        if check_response.status_code >= 500:
            raise SeriesManualImportError("Manual import validation failed")
        check_response.raise_for_status()

        command_response = await client.post(
            "/api/v3/command",
            json={
                "importMode": "copy",
                "name": "ManualImport",
                "files": files_payload,
            },
        )
        if command_response.status_code >= 400:
            raise SeriesManualImportError("Manual import command failed")
