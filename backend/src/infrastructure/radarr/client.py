"""HTTP-based Radarr service implementation."""

from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx

from src.application.interfaces.radarr import (
    MovieDetails,
    MovieImportFile,
    RadarrService,
)
from src.infrastructure.http import BaseHttpClient, HttpClientError

UNKNOWN_QUALITY_ID = 0
COMMAND_POLL_INTERVAL_SECONDS = 1.0
COMMAND_TIMEOUT_SECONDS = 300.0
COMMAND_SUCCESS_STATUS = "completed"
TERMINAL_COMMAND_STATUSES = frozenset({COMMAND_SUCCESS_STATUS, "failed", "aborted", "cancelled"})


class RadarrHttpClient(RadarrService):
    """Interact with Radarr's HTTP API."""

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
