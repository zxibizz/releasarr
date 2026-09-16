"""Common HTTP helpers shared across Sonarr and Radarr clients."""

from __future__ import annotations

import asyncio
import time
from typing import Any

from src.application.interfaces.arr import ArrQualityProfile, ArrRootFolder
from src.infrastructure.http import BaseHttpClient

UNKNOWN_QUALITY_ID = 0
COMMAND_POLL_INTERVAL_SECONDS = 1.0
COMMAND_TIMEOUT_SECONDS = 300.0
COMMAND_SUCCESS_STATUS = "completed"
TERMINAL_COMMAND_STATUSES = frozenset({COMMAND_SUCCESS_STATUS, "failed", "aborted", "cancelled"})


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


__all__ = [
    "COMMAND_POLL_INTERVAL_SECONDS",
    "COMMAND_SUCCESS_STATUS",
    "COMMAND_TIMEOUT_SECONDS",
    "TERMINAL_COMMAND_STATUSES",
    "UNKNOWN_QUALITY_ID",
    "ArrHttpClient",
]
