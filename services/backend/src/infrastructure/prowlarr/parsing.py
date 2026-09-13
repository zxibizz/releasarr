"""Lenient coercion helpers for Prowlarr payloads.

Prowlarr's JSON is generated from a .NET model where most fields are nullable and
a handful change shape between indexer implementations, so every read is treated
as untrusted rather than declared in a schema.
"""

from __future__ import annotations

from datetime import UTC, datetime

import httpx


def safe_str(value: object) -> str | None:
    if value is None:
        return None
    result = str(value).strip()
    return result or None


def safe_int(value: object) -> int | None:
    if not isinstance(value, int | float | str):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def safe_bool(value: object, *, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    return default


def safe_datetime(value: object) -> datetime | None:
    text = safe_str(value)
    if text is None:
        return None
    # Prowlarr sends ISO-8601, commonly with a trailing "Z" that
    # fromisoformat only accepts from Python 3.11 onwards.
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def safe_json(response: httpx.Response) -> dict[str, object] | None:
    try:
        payload = response.json()
    except ValueError:
        return None
    if isinstance(payload, dict):
        return payload
    return None


def safe_json_list(response: httpx.Response) -> list[object]:
    try:
        payload = response.json()
    except ValueError:
        return []
    if isinstance(payload, list):
        return payload
    return []


__all__ = [
    "safe_bool",
    "safe_datetime",
    "safe_int",
    "safe_json",
    "safe_json_list",
    "safe_str",
]
