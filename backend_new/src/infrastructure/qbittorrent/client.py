"""Async HTTP client for interacting with the qBittorrent Web API."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

import httpx


@dataclass(slots=True)
class QbittorrentClient:
    """Small wrapper over qBittorrent's Web API."""

    base_url: str
    username: str
    password: str
    timeout: float = 15.0
    _transport: httpx.BaseTransport | None = None
    _client: httpx.AsyncClient = field(init=False, repr=False)
    _logged_in: bool = field(init=False, default=False, repr=False)

    def __post_init__(self) -> None:
        self._client = httpx.AsyncClient(
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


__all__ = ["QbittorrentClient"]
