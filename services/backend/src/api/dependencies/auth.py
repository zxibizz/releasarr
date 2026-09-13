"""Authentication helpers for the API layer."""

from __future__ import annotations

import secrets

from fastapi import Header, status

from src.api.errors import api_error
from src.core.container import get_container


async def require_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:
    """Validate the API key header against configured settings.

    Fails closed: if no key is configured the server is misconfigured and all
    protected routes are denied rather than left open.
    """

    container = get_container()
    expected = container.settings.api_key.get_secret_value()
    if not expected:
        raise api_error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "server_misconfigured",
            "API key is not configured",
        )

    if x_api_key is None or not secrets.compare_digest(x_api_key, expected):
        raise api_error(status.HTTP_401_UNAUTHORIZED, "unauthorized", "Invalid API key")


__all__ = ["require_api_key"]
