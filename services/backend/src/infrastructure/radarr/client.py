"""HTTP-based Radarr service implementation."""

from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx

from src.application.interfaces.arr import ArrQualityProfile, ArrRootFolder
from src.application.interfaces.radarr import (
    MovieDetails,
    MovieImportFile,
    MovieLookup,
    RadarrService,
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

# Radarr only reports a movie as wanted once it reaches this availability, and
# anything stricter would hide a request from our own sync until release day.
MINIMUM_AVAILABILITY = "released"


class RadarrHttpClient(ArrHttpClient, RadarrService):
    """Interact with Radarr's HTTP API."""

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

    async def get_missing_movies(self) -> list[MovieDetails]:
        """Return the movies Radarr is still waiting for.

        Unlike Sonarr, whose wanted list is one row per missing episode, Radarr
        returns the whole movie resource per row, so no per-item follow-up call
        is needed to build the details.
        """

        payload = await self._request(
            "GET",
            "/wanted/missing",
            params={
                "page": 1,
                "pageSize": 1000,
                "sortDirection": "descending",
            },
        )

        records = payload.get("records", []) if isinstance(payload, dict) else []
        movies: list[MovieDetails] = []
        for entry in records:
            if not isinstance(entry, dict):
                continue
            movie = self._to_movie(entry)
            if movie is not None:
                movies.append(movie)
        return movies

    async def get_movie(self, movie_id: int) -> MovieDetails:
        data = await self._request("GET", f"/movie/{movie_id}")
        movie = self._to_movie(data if isinstance(data, dict) else {}, fallback_id=movie_id)
        if movie is None:
            raise HttpClientError(f"Radarr returned no usable movie for id {movie_id}")
        return movie

    async def manual_import(self, files: list[MovieImportFile]) -> bool:
        if not files:
            return True

        try:
            resolved = await self._reprocess(files)
            command_id = await self._run_import_command(files, resolved)
            return await self._await_command(command_id)
        except (HttpClientError, httpx.HTTPError):
            return False

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
                    # Absent on older Radarr versions, where every configured
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

    async def search_movies(self, term: str) -> list[MovieLookup]:
        payloads = await self._lookup(term)
        return [lookup for lookup in map(self._to_movie_lookup, payloads) if lookup is not None]

    async def lookup_movie(self, tmdb_id: int) -> MovieLookup | None:
        payload = await self._lookup_by_tmdb_id(tmdb_id)
        return None if payload is None else self._to_movie_lookup(payload)

    async def add_movie(
        self,
        *,
        tmdb_id: int,
        root_folder_path: str,
        quality_profile_id: int,
    ) -> int:
        """Add a movie to the library and return its Radarr id.

        The lookup payload is sent back to Radarr as it arrived, with only the
        library fields filled in, which is what Radarr's own add form does: it
        carries the title slug and images Radarr expects, and rebuilding those by
        hand risks disagreeing with its metadata.
        """

        payload = await self._lookup_by_tmdb_id(tmdb_id)
        if payload is None:
            raise HttpClientError(f"Radarr found no movie for TMDB id {tmdb_id}")

        payload["rootFolderPath"] = root_folder_path
        payload["qualityProfileId"] = quality_profile_id
        payload["monitored"] = True
        payload["minimumAvailability"] = MINIMUM_AVAILABILITY
        # Releasarr does its own grabbing through Prowlarr and qBittorrent.
        payload["addOptions"] = {"searchForMovie": False}

        created = await self._request("POST", "/movie", json=payload)
        movie_id = self._safe_int(created.get("id")) if isinstance(created, dict) else None
        if movie_id is None:
            raise HttpClientError(f"Radarr did not return an id for the added movie {tmdb_id}")
        return movie_id

    async def set_movie_monitored(self, movie_id: int, *, monitored: bool = True) -> None:
        """Set whether Radarr monitors a movie already in the library.

        An unmonitored movie stays out of Radarr's wanted list, and so out of our
        own sync: monitoring it is what stops a request sitting at completed
        forever, and unmonitoring it is what stops a removed request coming back
        on the next sync.
        """

        payload = await self._request("GET", f"/movie/{movie_id}")
        if not isinstance(payload, dict):
            raise HttpClientError(f"Radarr returned no movie for id {movie_id}")
        if bool(payload.get("monitored")) == monitored:
            return

        payload["monitored"] = monitored
        await self._request("PUT", f"/movie/{movie_id}", json=payload)

    async def _reprocess(self, files: list[MovieImportFile]) -> dict[str, dict[str, Any]]:
        """Run the files through Radarr's import preview, keyed by path.

        Serves two purposes. It validates the import while we can still react: the
        ``ManualImport`` command is queued and reports its outcome only in Radarr's
        own logs, so a file Radarr cannot read would otherwise look like a success
        and leave the release marked as exported. And it resolves the metadata the
        command would otherwise overwrite with blanks - see ``_command_payload``.
        """

        payload = await self._request(
            "POST",
            "/manualimport",
            json=[
                {
                    "path": file.path,
                    "movieId": file.movie_id,
                    # Radarr dereferences both, and only fills them in from the
                    # file name when they arrive as these "unknown" forms.
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
        files: list[MovieImportFile],
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
        """Block until Radarr has finished running the queued command.

        Radarr only queues the command, so returning as soon as it is accepted
        reports success before a single file has been copied, and leaves callers
        reading movie statistics that have not caught up yet. Waiting past the
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
        file: MovieImportFile,
        resolved: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Build one entry of the ``ManualImport`` command.

        The command applies quality, languages and the release fields verbatim,
        overwriting whatever it worked out from the file itself, so anything left
        out here is stored as unknown. The preview's values are passed straight
        back, which is also what Radarr's own interactive import does.
        """

        payload: dict[str, Any] = {
            "path": file.path,
            "movieId": file.movie_id,
            "folderName": file.folder_name,
        }
        if resolved is None:
            return payload

        for key in ("quality", "languages", "releaseGroup", "indexerFlags", "releaseType"):
            value = resolved.get(key)
            if value is not None:
                payload[key] = value
        return payload

    async def _lookup(self, term: str) -> list[dict[str, Any]]:
        data = await self._request("GET", "/movie/lookup", params={"term": term})
        if not isinstance(data, list):
            return []
        return [item for item in data if isinstance(item, dict)]

    async def _lookup_by_tmdb_id(self, tmdb_id: int) -> dict[str, Any] | None:
        payloads = await self._lookup(f"tmdb:{tmdb_id}")
        return payloads[0] if payloads else None

    def _to_movie_lookup(self, data: dict[str, Any]) -> MovieLookup | None:
        tmdb_id = self._safe_int(data.get("tmdbId"))
        if not tmdb_id:
            return None
        return MovieLookup(
            tmdb_id=tmdb_id,
            title=str(data.get("title") or ""),
            year=self._safe_int(data.get("year")),
            # Radarr reports a movie it does not hold with id 0.
            existing_movie_id=self._safe_int(data.get("id")) or None,
        )

    def _to_movie(
        self,
        data: dict[str, Any],
        fallback_id: int | None = None,
    ) -> MovieDetails | None:
        movie_id = self._safe_int(data.get("id")) or fallback_id
        if not movie_id:
            return None

        return MovieDetails(
            id=movie_id,
            title=str(data.get("title") or ""),
            year=self._safe_int(data.get("year")),
            overview=self._safe_str(data.get("overview")),
            poster_url=self._extract_poster_url(data.get("images") or []),
            imdb_id=self._safe_str(data.get("imdbId")),
            tmdb_id=self._safe_int(data.get("tmdbId")),
            genres=[str(genre) for genre in data.get("genres", []) if genre],
            runtime_minutes=self._safe_int(data.get("runtime")),
            has_file=bool(data.get("hasFile")),
        )

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        # Checked per request rather than in __init__ so that series-only
        # deployments can still build the container without a Radarr key.
        if not self._api_key:
            raise HttpClientError("Radarr API key is not configured; set RELEASARR_RADARR_API_KEY")
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


__all__ = ["RadarrHttpClient"]
