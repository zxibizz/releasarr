"""Tests for the shared BaseHttpClient retry/backoff behaviour."""

from __future__ import annotations

import httpx
import pytest

from src.infrastructure.http import BaseHttpClient, HttpClientError


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _instant(_: float) -> None:
        return None

    monkeypatch.setattr("src.infrastructure.http.base.asyncio.sleep", _instant)


async def test_retries_transient_status_then_succeeds() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] < 3:
            return httpx.Response(503)
        return httpx.Response(200, json={"ok": True})

    client = BaseHttpClient(transport=httpx.MockTransport(handler), backoff_base=0.0)
    try:
        body = await client.request_json("GET", "https://example.test/x")
    finally:
        await client.aclose()

    assert body == {"ok": True}
    assert calls["n"] == 3


async def test_retries_exhausted_returns_last_response() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    client = BaseHttpClient(transport=httpx.MockTransport(handler), retries=2, backoff_base=0.0)
    try:
        response = await client.request("GET", "https://example.test/x")
    finally:
        await client.aclose()

    assert response.status_code == 503


async def test_transport_error_is_wrapped() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom", request=request)

    client = BaseHttpClient(transport=httpx.MockTransport(handler), retries=1, backoff_base=0.0)
    try:
        with pytest.raises(HttpClientError):
            await client.request("GET", "https://example.test/x")
    finally:
        await client.aclose()
