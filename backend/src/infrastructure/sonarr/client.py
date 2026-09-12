"""HTTP-based Sonarr service implementation."""

from __future__ import annotations

import asyncio
import time
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

UNKNOWN_QUALITY_ID = 0
COMMAND_POLL_INTERVAL_SECONDS = 1.0
COMMAND_TIMEOUT_SECONDS = 300.0
COMMAND_SUCCESS_STATUS = "completed"
TERMINAL_COMMAND_STATUSES = frozenset({COMMAND_SUCCESS_STATUS, "failed", "aborted", "cancelled"})


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

        try:
            resolved = await self._reprocess(files)
            command_id = await self._run_import_command(files, resolved)
            return await self._await_command(command_id)
        except (HttpClientError, httpx.HTTPError):
            return False

    async def _reprocess(self, files: list[ManualImportFile]) -> dict[str, dict[str, Any]]:
        """Run the files through Sonarr's import preview, keyed by path.

        Serves two purposes. It validates the import while we can still react: the
        ``ManualImport`` command is queued and reports its outcome only in Sonarr's
        own logs, so a file Sonarr cannot read would otherwise look like a success
        and leave the release marked as exported. And it resolves the metadata the
        command would otherwise overwrite with blanks - see ``_command_payload``.
        """

        payload = await self._request(
            "POST",
            "/manualimport",
            json=[
                {
                    "path": file.path,
                    "seriesId": file.series_id,
                    "episodeIds": file.episode_ids,
                    # Sonarr dereferences both, and only fills them in from the file
                    # name when they arrive as these "unknown" forms.
                    "quality": {"quality": {"id": UNKNOWN_QUALITY_ID}},
                    "languages": [],
                }
                for file in files
            ],
        )

        if not isinstance(payload, list):
            return {}
        return {
            str(item.get("path")): item
            for item in payload
            if isinstance(item, dict) and item.get("path")
        }

    async def _run_import_command(
        self,
        files: list[ManualImportFile],
        resolved: dict[str, dict[str, Any]],
    ) -> int | None:
        payload = await self._request(
            "POST",
            "/command",
            json={
                "name": "ManualImport",
                "files": [self._command_payload(file, resolved.get(file.path)) for file in files],
                # Copy rather than move: the files belong to a torrent we keep seeding.
                "importMode": "copy",
            },
        )
        if not isinstance(payload, dict):
            return None
        return self._safe_int(payload.get("id"))

    async def _await_command(self, command_id: int | None) -> bool:
        """Block until Sonarr has finished running the queued command.

        Sonarr only queues the command, so returning as soon as it is accepted
        reports success before a single file has been copied, and leaves callers
        reading series statistics that have not caught up yet. Waiting past the
        timeout is not treated as a failure: the import is still running and
        re-queueing it would just duplicate the work.
        """

        if command_id is None:
            return True

        deadline = time.monotonic() + COMMAND_TIMEOUT_SECONDS
        while True:
            payload = await self._request("GET", f"/command/{command_id}")
            status = str(payload.get("status") or "") if isinstance(payload, dict) else ""
            if status in TERMINAL_COMMAND_STATUSES:
                return status == COMMAND_SUCCESS_STATUS
            if time.monotonic() >= deadline:
                return True
            await asyncio.sleep(COMMAND_POLL_INTERVAL_SECONDS)

    def _command_payload(
        self,
        file: ManualImportFile,
        resolved: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Build one entry of the ``ManualImport`` command.

        The command applies quality, languages and the release fields verbatim,
        overwriting whatever it worked out from the file itself, so anything left
        out here is stored as unknown. The preview's values are passed straight
        back, which is also what Sonarr's own interactive import does.
        """

        payload: dict[str, Any] = {
            "path": file.path,
            "seriesId": file.series_id,
            "episodeIds": file.episode_ids,
            "folderName": file.folder_name,
        }
        if resolved is None:
            return payload

        for key in ("quality", "languages", "releaseGroup", "indexerFlags", "releaseType"):
            value = resolved.get(key)
            if value is not None:
                payload[key] = value
        return payload

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
