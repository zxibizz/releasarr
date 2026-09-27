"""Tests for how the API resolves a caller's credentials."""

from __future__ import annotations

import pytest

from src.api.dependencies import auth as auth_dependencies
from src.api.dependencies.auth import get_principal


class RecordingAuthenticator:
    def __init__(self) -> None:
        self.service_keys: list[str] = []

    async def authenticate_service_key(self, key: str) -> str:
        self.service_keys.append(key)
        return "principal"


@pytest.fixture()
def authenticator(monkeypatch: pytest.MonkeyPatch) -> RecordingAuthenticator:
    fake = RecordingAuthenticator()
    monkeypatch.setattr(auth_dependencies, "_authenticate_use_case", lambda: fake)
    return fake


@pytest.mark.asyncio
async def test_the_service_key_is_read_from_the_apikey_query_parameter(
    authenticator: RecordingAuthenticator,
) -> None:
    principal = await get_principal(authorization=None, x_api_key=None, apikey="rlsr_query")

    assert principal == "principal"
    assert authenticator.service_keys == ["rlsr_query"]


@pytest.mark.asyncio
async def test_the_header_wins_over_the_query_parameter(
    authenticator: RecordingAuthenticator,
) -> None:
    await get_principal(authorization=None, x_api_key="rlsr_header", apikey="rlsr_query")

    assert authenticator.service_keys == ["rlsr_header"]


@pytest.mark.asyncio
async def test_no_credentials_resolve_to_no_principal(
    authenticator: RecordingAuthenticator,
) -> None:
    assert await get_principal(authorization=None, x_api_key=None, apikey=None) is None
    assert authenticator.service_keys == []
