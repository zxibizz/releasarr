"""HTTP-based Sonarr service implementation."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

import httpx

from src.application.interfaces.arr import ArrQualityProfile, ArrRootFolder
from src.application.interfaces.sonarr import (
    ManualImportFile,
    MissingSeriesRecord,
    SeriesDetails,
    SeriesLookup,
    SeriesSeasonDetails,
    SonarrEpisode,
    SonarrService,
)
from src.infrastructure.arr.base import (
    COMMAND_POLL_INTERVAL_SECONDS,
    COMMAND_SUCCESS_STATUS,
    COMMAND_TIMEOUT_SECONDS,
    TERMINAL_COMMAND_STATUSES,
    UNKNOWN_QUALITY_ID,
    ArrHttpClient,
)
from src.infrastructure.http import BaseHttpClient, HttpClientError

# How Sonarr spells "monitor seasons added after this series was", on the series
# itself rather than in the one-off add options.
MONITOR_NEW_ITEMS_ALL = "all"
MONITOR_NEW_ITEMS_NONE = "none"

# Sonarr refreshes a freshly added series in the background, so its episodes -
# and with them the season episode counts - appear a moment after the add call
# returns.
REFRESH_POLL_INTERVAL_SECONDS = 1.0
REFRESH_TIMEOUT_SECONDS = 30.0


class SonarrHttpClient(ArrHttpClient, SonarrService):
    """Interact with Sonarr's HTTP API."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        timeout_seconds: float = 15.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._api_key = api_key
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

        return self._to_series_details(data, fallback_id=series_id)

    async def get_root_folders(self) -> list[ArrRootFolder]:
        data = await self._request("GET", "/rootfolder")
        if not isinstance(data, list):
            return []

        folders: list[ArrRootFolder] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            path = self._safe_str(item.get("path"))
            if not path:
                continue
            folders.append(
                ArrRootFolder(
                    path=path,
                    free_space=self._safe_int(item.get("freeSpace")),
                    # Absent on older Sonarr versions, where every configured
                    # folder is assumed reachable.
                    accessible=bool(item.get("accessible", True)),
                )
            )
        return folders

    async def get_quality_profiles(self) -> list[ArrQualityProfile]:
        data = await self._request("GET", "/qualityprofile")
        if not isinstance(data, list):
            return []

        profiles: list[ArrQualityProfile] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            profile_id = self._safe_int(item.get("id"))
            if profile_id is None:
                continue
            profiles.append(
                ArrQualityProfile(id=profile_id, name=str(item.get("name") or profile_id))
            )
        return profiles

    async def search_series(self, term: str) -> list[SeriesLookup]:
        payloads = await self._lookup(term)
        return [lookup for lookup in map(self._to_series_lookup, payloads) if lookup is not None]

    async def lookup_series(self, tvdb_id: int) -> SeriesLookup | None:
        payload = await self._lookup_by_tvdb_id(tvdb_id)
        return None if payload is None else self._to_series_lookup(payload)

    async def add_series(
        self,
        *,
        tvdb_id: int,
        root_folder_path: str,
        quality_profile_id: int,
        monitored_seasons: Sequence[int],
        monitor_new_seasons: bool = False,
    ) -> int:
        """Add a series to the library, monitoring only the requested seasons.

        The lookup payload is sent back to Sonarr as it arrived, with only the
        library fields filled in, which is what Sonarr's own add form does: it
        carries the title slug, images and season list Sonarr expects, and
        rebuilding those by hand risks disagreeing with its metadata.
        """

        payload = await self._lookup_by_tvdb_id(tvdb_id)
        if payload is None:
            raise HttpClientError(f"Sonarr found no series for TVDB id {tvdb_id}")

        wanted = set(monitored_seasons)
        payload["rootFolderPath"] = root_folder_path
        payload["qualityProfileId"] = quality_profile_id
        payload["monitored"] = True
        payload["seasonFolder"] = True
        payload["monitorNewItems"] = self._monitor_new_items(monitor_new_seasons)
        payload["seasons"] = [
            {**season, "monitored": self._season_number(season) in wanted}
            for season in payload.get("seasons") or []
            if isinstance(season, dict)
        ]
        payload["addOptions"] = {
            # Monitors the episodes of the seasons flagged above. Without it the
            # episodes arrive unmonitored, which keeps them out of Sonarr's
            # wanted list and so out of our own sync.
            "monitor": "all",
            # Releasarr does its own grabbing through Prowlarr and qBittorrent.
            "searchForMissingEpisodes": False,
            "searchForCutoffUnmetEpisodes": False,
        }

        created = await self._request("POST", "/series", json=payload)
        series_id = self._safe_int(created.get("id")) if isinstance(created, dict) else None
        if series_id is None:
            raise HttpClientError(f"Sonarr did not return an id for the added series {tvdb_id}")
        return series_id

    async def apply_season_monitoring(
        self,
        series_id: int,
        *,
        monitor: Sequence[int] = (),
        unmonitor: Sequence[int] = (),
        monitor_new_seasons: bool | None = None,
    ) -> None:
        """Monitor and unmonitor the named seasons of a series in the library.

        Seasons nobody named are left exactly as they are. A user may monitor a
        season outside releasarr, and rewriting the whole selection from the
        seasons we happen to hold requests for would drop those episodes out of
        Sonarr's wanted list behind their back.

        The series flag follows its seasons: it goes on for the first season
        monitored and comes off once the last one is dropped, so a series
        nothing is wanted from reads as unmonitored in Sonarr rather than as
        monitored and asking for nothing. A series still set to pick up seasons
        that have yet to air wants something, and stays on with no season of
        its own monitored.
        """

        payload = await self._request("GET", f"/series/{series_id}")
        if not isinstance(payload, dict):
            raise HttpClientError(f"Sonarr returned no series for id {series_id}")

        # Monitoring wins over unmonitoring, so a season named in both is kept
        # rather than silently dropped.
        wanted = set(monitor)
        unwanted = set(unmonitor) - wanted
        seasons = [season for season in payload.get("seasons") or [] if isinstance(season, dict)]
        updated = [self._with_monitoring(season, wanted, unwanted) for season in seasons]

        wants_new_seasons = (
            self._reads_monitor_new_items(payload)
            if monitor_new_seasons is None
            else monitor_new_seasons
        )
        wants_series = wants_new_seasons or any(season.get("monitored") for season in updated)

        if (
            updated == seasons
            and bool(payload.get("monitored")) == wants_series
            and wants_new_seasons == self._reads_monitor_new_items(payload)
        ):
            return

        payload["seasons"] = updated
        payload["monitored"] = wants_series
        payload["monitorNewItems"] = self._monitor_new_items(wants_new_seasons)
        await self._request("PUT", f"/series/{series_id}", json=payload)

    async def wait_for_series_episodes(
        self,
        series_id: int,
        season_numbers: Sequence[int],
        timeout_seconds: float | None = None,
    ) -> SeriesDetails:
        """Poll a series until Sonarr reports episodes for the given seasons.

        A series added a moment ago still has no episodes, so reading its season
        statistics right away records every request as holding zero episodes.
        Timing out is not an error: the counts are refreshed by the next sync,
        and failing the add over them would be worse than a stale number.
        """

        timeout = REFRESH_TIMEOUT_SECONDS if timeout_seconds is None else timeout_seconds
        deadline = time.monotonic() + timeout
        while True:
            details = await self.get_series(series_id)
            if self._seasons_populated(details, season_numbers):
                return details
            if time.monotonic() >= deadline:
                return details
            await asyncio.sleep(REFRESH_POLL_INTERVAL_SECONDS)

    async def get_episodes(self, series_id: int) -> list[SonarrEpisode]:
        # The file rides along rather than being fetched per episode: it is the
        # only place Sonarr reports the size, and asking for it here costs the
        # one call we were making anyway.
        data = await self._request(
            "GET",
            "/episode",
            params={"seriesId": series_id, "includeEpisodeFile": "true"},
        )
        if not isinstance(data, list):
            return []

        episodes = []
        for item in data:
            episodes.append(
                SonarrEpisode(
                    id=int(item.get("id") or 0),
                    season_number=int(item.get("seasonNumber") or 0),
                    episode_number=int(item.get("episodeNumber") or 0),
                    title=str(item.get("title") or ""),
                    air_date=self._air_date(item),
                    has_file=bool(item.get("hasFile")),
                    file_size=self._file_size(item),
                )
            )
        return episodes

    def _file_size(self, item: dict[str, Any]) -> int | None:
        """Bytes on disk, or nothing when Sonarr reports no file to measure.

        A zero is discarded along with a missing file: Sonarr reports one for a
        file it has yet to measure, and a size of nothing is not something worth
        showing as though it were.
        """

        file = item.get("episodeFile")
        if not isinstance(file, dict):
            return None
        try:
            size = int(file.get("size") or 0)
        except (TypeError, ValueError):
            return None
        return size or None

    def _air_date(self, item: dict[str, Any]) -> datetime | None:
        """Read an episode's broadcast time, preferring the one Sonarr zones.

        ``airDateUtc`` is a timestamp and ``airDate`` a bare calendar date in the
        series' own timezone; the latter is all Sonarr has for some episodes, and
        reading it as midnight UTC is close enough for the day to come out right.
        """

        text = item.get("airDateUtc") or item.get("airDate")
        if not isinstance(text, str) or not text:
            return None
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)

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

    def _seasons_populated(self, details: SeriesDetails, season_numbers: Sequence[int]) -> bool:
        for season_number in season_numbers:
            season = details.seasons.get(season_number)
            if season is None or season.total_episode_count <= 0:
                return False
        return True

    async def _lookup(self, term: str) -> list[dict[str, Any]]:
        data = await self._request("GET", "/series/lookup", params={"term": term})
        if not isinstance(data, list):
            return []
        return [item for item in data if isinstance(item, dict)]

    async def _lookup_by_tvdb_id(self, tvdb_id: int) -> dict[str, Any] | None:
        payloads = await self._lookup(f"tvdb:{tvdb_id}")
        return payloads[0] if payloads else None

    def _to_series_lookup(self, data: dict[str, Any]) -> SeriesLookup | None:
        tvdb_id = self._safe_int(data.get("tvdbId"))
        if not tvdb_id:
            return None

        season_numbers: list[int] = []
        monitored_seasons: list[int] = []
        for season in data.get("seasons") or []:
            if not isinstance(season, dict):
                continue
            season_number = self._season_number(season)
            if season_number is None:
                continue
            season_numbers.append(season_number)
            if season.get("monitored"):
                monitored_seasons.append(season_number)

        return SeriesLookup(
            tvdb_id=tvdb_id,
            title=str(data.get("title") or ""),
            year=self._safe_int(data.get("year")),
            # Sonarr reports a series it does not hold with id 0.
            existing_series_id=self._safe_int(data.get("id")) or None,
            season_numbers=sorted(set(season_numbers)),
            monitored_seasons=sorted(set(monitored_seasons)),
        )

    def _to_series_details(self, data: Any, *, fallback_id: int) -> SeriesDetails:
        if not isinstance(data, dict):
            data = {}

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
                monitored=bool(season_data.get("monitored")),
            )

        return SeriesDetails(
            id=int(data.get("id") or fallback_id),
            title=str(data.get("title") or ""),
            year=self._safe_int(data.get("year")),
            overview=self._safe_str(data.get("overview")),
            poster_url=self._extract_poster_url(data.get("images") or []),
            imdb_id=self._safe_str(data.get("imdbId")),
            tvdb_id=self._safe_int(data.get("tvdbId")),
            genres=[str(genre) for genre in data.get("genres", []) if genre],
            seasons=seasons,
            monitor_new_seasons=self._reads_monitor_new_items(data),
        )

    def _season_number(self, season: dict[str, Any]) -> int | None:
        return self._safe_int(season.get("seasonNumber"))

    def _with_monitoring(
        self,
        season: dict[str, Any],
        wanted: set[int],
        unwanted: set[int],
    ) -> dict[str, Any]:
        season_number = self._season_number(season)
        if season_number in wanted:
            return {**season, "monitored": True}
        if season_number in unwanted:
            return {**season, "monitored": False}
        return season

    def _monitor_new_items(self, monitor_new_seasons: bool) -> str:
        return MONITOR_NEW_ITEMS_ALL if monitor_new_seasons else MONITOR_NEW_ITEMS_NONE

    def _reads_monitor_new_items(self, data: dict[str, Any]) -> bool:
        return str(data.get("monitorNewItems") or "").lower() == MONITOR_NEW_ITEMS_ALL

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        # Checked per request rather than in __init__ so that movie-only
        # deployments can still build the container without a Sonarr key.
        if not self._api_key:
            raise HttpClientError("Sonarr API key is not configured; set RELEASARR_SONARR_API_KEY")
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
