"""Helpers for cached metadata fetches from external providers."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Protocol, TypeVar

T = TypeVar("T")


class SupportsWarning(Protocol):
    def warning(self, message: str, **kwargs: object) -> None: ...


async def get_cached_metadata(
    *,
    cache: dict[int, T | None],
    lookup_id: int,
    fetch: Callable[[], Awaitable[T]],
    logger: SupportsWarning,
    provider_name: str,
    entity_id: int,
    lookup_field: str,
    warning_message: str,
) -> T | None:
    """Return cached metadata or fetch it, caching failures as None."""

    if lookup_id in cache:
        return cache[lookup_id]

    try:
        metadata = await fetch()
    except Exception as exc:  # pragma: no cover - defensive against HTTP failures
        logger.warning(
            warning_message,
            error=str(exc),
            **{provider_name: entity_id, lookup_field: lookup_id},
        )
        cache[lookup_id] = None
        return None

    cache[lookup_id] = metadata
    return metadata
