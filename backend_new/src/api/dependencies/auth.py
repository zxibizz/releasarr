"""Authentication helpers for the API layer."""

from __future__ import annotations

from fastapi import Header, status

from src.api.errors import api_error
from src.core.container import get_container


async def require_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:
    """Validate API key header against configured settings."""

    container = get_container()
    expected = container.settings.api_key
    if not expected:
        return
    if x_api_key != expected:
        raise api_error(status.HTTP_401_UNAUTHORIZED, "unauthorized", "Invalid API key")


__all__ = ["require_api_key"]
