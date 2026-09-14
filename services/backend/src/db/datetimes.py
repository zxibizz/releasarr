"""Normalising timestamps that have been through the database.

``DateTime(timezone=True)`` is a promise Postgres keeps and SQLite does not: the
column round-trips through ``timestamptz`` there, but SQLite has no aware
timestamp type at all, so the same column comes back naive. Everything is
written in UTC, so a naive value read back is UTC too — it just has to be told
so before anything compares it to ``datetime.now(UTC)``.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import overload


@overload
def as_utc(value: datetime) -> datetime: ...


@overload
def as_utc(value: None) -> None: ...


def as_utc(value: datetime | None) -> datetime | None:
    """Return ``value`` as an aware UTC datetime, reading naive values as UTC."""

    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


__all__ = ["as_utc"]
