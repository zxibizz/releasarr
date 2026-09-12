"""Shared HTTP client foundation for outbound service integrations.

Provides a persistent :class:`httpx.AsyncClient` with sensible defaults,
transient-error retry with exponential backoff, and a common error type so the
individual service clients don't each reinvent connection handling.
"""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from typing import Any

import httpx

DEFAULT_TIMEOUT = 15.0
DEFAULT_RETRIES = 2
DEFAULT_BACKOFF_BASE = 0.2
RETRY_STATUS_CODES = frozenset({429, 500, 502, 503, 504})


class HttpClientError(RuntimeError):
    """Raised when an outbound request ultimately fails (after retries)."""


def build_async_client(
    *,
    base_url: str = "",
    headers: Mapping[str, str] | None = None,
    timeout: float = DEFAULT_TIMEOUT,
    transport: httpx.AsyncBaseTransport | None = None,
    auth: httpx.Auth | None = None,
) -> httpx.AsyncClient:
    """Construct an :class:`httpx.AsyncClient` with the project's defaults."""

    return httpx.AsyncClient(
        base_url=base_url.rstrip("/") if base_url else base_url,
        headers=dict(headers or {}),
        timeout=httpx.Timeout(timeout),
        transport=transport,
        auth=auth,
    )


class BaseHttpClient:
    """A thin wrapper over ``httpx.AsyncClient`` adding retry/backoff."""

    def __init__(
        self,
        *,
        base_url: str = "",
        headers: Mapping[str, str] | None = None,
        timeout: float = DEFAULT_TIMEOUT,
        transport: httpx.AsyncBaseTransport | None = None,
        auth: httpx.Auth | None = None,
        retries: int = DEFAULT_RETRIES,
        backoff_base: float = DEFAULT_BACKOFF_BASE,
    ) -> None:
        self._client = build_async_client(
            base_url=base_url,
            headers=headers,
            timeout=timeout,
            transport=transport,
            auth=auth,
        )
        self._retries = retries
        self._backoff_base = backoff_base

    async def aclose(self) -> None:
        await self._client.aclose()

    async def request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        """Perform a request, retrying transient failures with backoff."""

        attempt = 0
        while True:
            try:
                response = await self._client.request(method, url, **kwargs)
            except httpx.TransportError as exc:
                if attempt >= self._retries:
                    raise HttpClientError(f"request to {url!r} failed: {exc}") from exc
                await self._backoff(attempt)
                attempt += 1
                continue

            if response.status_code in RETRY_STATUS_CODES and attempt < self._retries:
                await self._backoff(attempt)
                attempt += 1
                continue
            return response

    async def request_json(self, method: str, url: str, **kwargs: Any) -> Any:
        """Perform a request and return the parsed JSON body."""

        response = await self.request(method, url, **kwargs)
        response.raise_for_status()
        return response.json()

    async def _backoff(self, attempt: int) -> None:
        await asyncio.sleep(self._backoff_base * (2**attempt))


__all__ = ["BaseHttpClient", "HttpClientError", "build_async_client"]
