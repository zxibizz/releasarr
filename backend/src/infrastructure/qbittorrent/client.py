"""Async HTTP client for interacting with the qBittorrent Web API."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

import httpx

from src.infrastructure.http import build_async_client


@dataclass(slots=True)
class QbittorrentClient:
    """Small wrapper over qBittorrent's Web API."""

    base_url: str
    username: str
    password: str
    timeout: float = 15.0
    _transport: httpx.AsyncBaseTransport | None = None
    _client: httpx.AsyncClient = field(init=False, repr=False)
    _logged_in: bool = field(init=False, default=False, repr=False)

    def __post_init__(self) -> None:
        self._client = build_async_client(
            base_url=self.base_url,
            timeout=self.timeout,
            transport=self._transport,
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def add_magnet(
        self,
        magnet_link: str,
        *,
        save_path: str | None = None,
        category: str | None = None,
        tags: Sequence[str] | None = None,
        paused: bool = False,
    ) -> None:
        """Add a magnet link to the client."""

        data = self._build_payload(save_path, category, tags, paused)
        data["urls"] = magnet_link
        await self._post("/torrents/add", data=data)

    async def add_torrent(
        self,
        torrent_bytes: bytes,
        *,
        save_path: str | None = None,
        category: str | None = None,
        tags: Sequence[str] | None = None,
        paused: bool = False,
    ) -> None:
        """Upload raw torrent data to the client."""

        data = self._build_payload(save_path, category, tags, paused)
        files = {
            "fileselect[]": (
                "download.torrent",
                torrent_bytes,
                "application/x-bittorrent",
            )
        }
        await self._post("/torrents/add", data=data, files=files)

    async def _post(
        self,
        url: str,
        *,
        data: dict[str, str],
        files: dict[str, tuple[str, bytes, str]] | None = None,
    ) -> None:
        await self._ensure_login()
        try:
            response = await self._client.post(url, data=data, files=files)
            if response.status_code == httpx.codes.FORBIDDEN:
                # Session expired; retry once after re-authenticating.
                self._logged_in = False
                await self._ensure_login()
                response = await self._client.post(url, data=data, files=files)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:  # pragma: no cover - defensive network errors
            raise RuntimeError(f"qBittorrent request failed: {exc.response.text}") from exc
        except httpx.HTTPError as exc:  # pragma: no cover - connection issues
            raise RuntimeError(f"qBittorrent request failed: {exc!s}") from exc

    async def _ensure_login(self) -> None:
        if self._logged_in:
            return
        try:
            response = await self._client.post(
                "/auth/login",
                data={"username": self.username, "password": self.password},
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:  # pragma: no cover - authentication failures
            raise RuntimeError("qBittorrent authentication failed") from exc
        except httpx.HTTPError as exc:  # pragma: no cover - connection issues
            raise RuntimeError(f"qBittorrent authentication failed: {exc!s}") from exc
        self._logged_in = True

    async def pause_torrent(self, info_hash: str) -> bool:
        """Pause a torrent by info hash. Returns True on success."""
        await self._ensure_login()
        try:
            response = await self._client.post(
                "/torrents/pause",
                data={"hashes": info_hash.lower()},
            )
            if response.status_code == httpx.codes.FORBIDDEN:
                self._logged_in = False
                await self._ensure_login()
                response = await self._client.post(
                    "/torrents/pause",
                    data={"hashes": info_hash.lower()},
                )
            return response.status_code == httpx.codes.OK
        except httpx.HTTPError:
            return False

    async def resume_torrent(self, info_hash: str) -> bool:
        """Resume a torrent by info hash. Returns True on success."""
        await self._ensure_login()
        try:
            response = await self._client.post(
                "/torrents/resume",
                data={"hashes": info_hash.lower()},
            )
            if response.status_code == httpx.codes.FORBIDDEN:
                self._logged_in = False
                await self._ensure_login()
                response = await self._client.post(
                    "/torrents/resume",
                    data={"hashes": info_hash.lower()},
                )
            return response.status_code == httpx.codes.OK
        except httpx.HTTPError:
            return False

    async def get_torrent(self, info_hash: str) -> dict[str, Any] | None:
        """Get torrent info by hash. Returns None if not found."""
        await self._ensure_login()
        try:
            response = await self._client.get(
                "/torrents/info",
                params={"hashes": info_hash.lower()},
            )
            if response.status_code == httpx.codes.FORBIDDEN:
                self._logged_in = False
                await self._ensure_login()
                response = await self._client.get(
                    "/torrents/info",
                    params={"hashes": info_hash.lower()},
                )
            response.raise_for_status()
            torrents = response.json()
            if torrents and isinstance(torrents, list) and len(torrents) > 0:
                return torrents[0]
            return None
        except httpx.HTTPError:
            return None

    async def list_torrents(
        self,
        category: str | None = None,
        tag: str | None = None,
    ) -> list[dict[str, Any]]:
        """List all torrents, optionally filtered by category or tag."""
        await self._ensure_login()
        params: dict[str, str] = {}
        if category:
            params["category"] = category
        if tag:
            params["tag"] = tag
        try:
            response = await self._client.get("/torrents/info", params=params)
            if response.status_code == httpx.codes.FORBIDDEN:
                self._logged_in = False
                await self._ensure_login()
                response = await self._client.get("/torrents/info", params=params)
            response.raise_for_status()
            result = response.json()
            return result if isinstance(result, list) else []
        except httpx.HTTPError:
            return []

    def _build_payload(
        self,
        save_path: str | None,
        category: str | None,
        tags: Sequence[str] | None,
        paused: bool,
    ) -> dict[str, str]:
        payload: dict[str, str] = {
            "autoTMM": "false",
            "paused": "true" if paused else "false",
            "contentLayout": "Original",
            "dlLimit": "NaN",
            "upLimit": "NaN",
        }
        if save_path:
            payload["savepath"] = save_path
        if category:
            payload["category"] = category
        if tags:
            payload["tags"] = ",".join(tag for tag in tags if tag)
        return payload

    async def delete_torrent(self, info_hash: str, delete_files: bool = False) -> None:
        """Delete a torrent by info hash."""
        await self._ensure_login()
        try:
            response = await self._client.post(
                "/torrents/delete",
                data={
                    "hashes": info_hash.lower(),
                    "deleteFiles": "true" if delete_files else "false",
                },
            )
            if response.status_code == httpx.codes.FORBIDDEN:
                self._logged_in = False
                await self._ensure_login()
                response = await self._client.post(
                    "/torrents/delete",
                    data={
                        "hashes": info_hash.lower(),
                        "deleteFiles": "true" if delete_files else "false",
                    },
                )
            if response.status_code != httpx.codes.NOT_FOUND:
                response.raise_for_status()
        except httpx.HTTPError:
            # Swallow network/client errors to allow DB cleanup
            pass
        return None


__all__ = ["QbittorrentClient"]
