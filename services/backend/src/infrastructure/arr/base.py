"""Common HTTP helpers shared across Sonarr and Radarr clients."""

from __future__ import annotations

import asyncio
import time
from datetime import UTC, datetime
from typing import Any

from src.application.interfaces.arr import ArrImportEvent, ArrQualityProfile, ArrRootFolder
from src.infrastructure.http import BaseHttpClient

UNKNOWN_QUALITY_ID = 0
COMMAND_POLL_INTERVAL_SECONDS = 1.0
COMMAND_TIMEOUT_SECONDS = 300.0
COMMAND_SUCCESS_STATUS = "completed"
TERMINAL_COMMAND_STATUSES = frozenset({COMMAND_SUCCESS_STATUS, "failed", "aborted", "cancelled"})
# Both apps number the history event of a file imported from outside the
# library the same way.
DOWNLOAD_FOLDER_IMPORTED_EVENT = 3


class ArrHttpClient(BaseHttpClient):
    """Common logic for Sonarr and Radarr integrations."""

    # Held by each concrete client, which builds it with its own base URL and
    # API key. Declared here so the shared helpers below can reach it.
    _http: BaseHttpClient

    async def get_root_folders(self) -> list[ArrRootFolder]:
        raise NotImplementedError

    async def get_quality_profiles(self) -> list[ArrQualityProfile]:
        raise NotImplementedError

    async def _request_no_content(self, method: str, path: str, **kwargs: Any) -> None:
        """Perform a request whose answer is empty on success, such as a delete."""

        self._require_api_key()
        await self._http.request_no_content(method, path, **kwargs)

    def _require_api_key(self) -> None:
        """Raise when this client has no key to reach its app with."""
        raise NotImplementedError

    async def _await_command(self, command_id: int | None) -> bool:
        """Wait for an Arr command to finish before returning success."""

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

    def _import_events(self, payload: object, target_key: str) -> list[ArrImportEvent]:
        """Read history records of imports into the events the export compares against.

        The record's ``data`` carries the file id and the source path as strings.
        Keys are matched without regard to case, since the two apps and their
        versions do not agree on how a dictionary key is cased.
        """

        if not isinstance(payload, list):
            return []

        events = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            data = item.get("data")
            if not isinstance(data, dict):
                continue
            fields = {str(key).lower(): value for key, value in data.items()}
            target_id = self._safe_int(item.get(target_key))
            file_id = self._safe_int(fields.get("fileid"))
            source_path = self._safe_str(fields.get("droppedpath"))
            date = self._history_date(item.get("date"))
            if not target_id or not file_id or not source_path or date is None:
                continue
            events.append(
                ArrImportEvent(
                    target_id=target_id,
                    file_id=file_id,
                    source_path=source_path,
                    date=date,
                )
            )
        return events

    @staticmethod
    def _history_date(value: object) -> datetime | None:
        if not isinstance(value, str) or not value:
            return None
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)

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

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        raise NotImplementedError

    async def test_connection(self) -> None:
        """Verify the URL and API key reach the app via its cheapest status probe.

        Implemented here once: both Sonarr and Radarr answer ``/system/status``
        the same way, and a 401/403 is the auth failure a saved key should show.
        """

        await self._request("GET", "/system/status")


__all__ = [
    "COMMAND_POLL_INTERVAL_SECONDS",
    "COMMAND_SUCCESS_STATUS",
    "COMMAND_TIMEOUT_SECONDS",
    "TERMINAL_COMMAND_STATUSES",
    "UNKNOWN_QUALITY_ID",
    "ArrHttpClient",
]
