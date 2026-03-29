"""Interfaces supporting media request use cases."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from src.domain.enums import MediaRequestStatus, MediaType


@dataclass(slots=True)
class MediaRequestRecord:
    """Normalized representation of a media request."""

    id: str
    media_type: MediaType
    status: MediaRequestStatus
    title: str
    year: int
    overview: str | None
    poster_url: str | None
    genres: list[str]
    runtime_minutes: int | None
    imdb_id: str | None
    season_number: int | None
    total_episodes: int | None
    series_title: str | None
    series_year: int | None
    created_at: datetime
    updated_at: datetime


@dataclass(slots=True)
class CreateMediaRequestData:
    """Payload required to persist a new media request."""

    id: str
    media_type: MediaType
    title: str
    year: int
    overview: str | None
    poster_url: str | None
    genres: list[str]
    runtime_minutes: int | None
    imdb_id: str | None
    season_number: int | None
    total_episodes: int | None
    series_title: str | None
    series_year: int | None
    status: MediaRequestStatus


@dataclass(slots=True)
class UpdateMediaRequestData:
    """Fields that may be updated on an existing media request."""

    title: str | None = None
    year: int | None = None
    poster_url: str | None = None
    overview: str | None = None
    genres: list[str] | None = None
    status: MediaRequestStatus | None = None
    runtime_minutes: int | None = None
    imdb_id: str | None = None
    season_number: int | None = None
    total_episodes: int | None = None
    series_title: str | None = None
    series_year: int | None = None


class MediaRequestRepository(Protocol):
    """Protocol describing persistence operations for media requests."""

    async def list_requests(
        self,
        *,
        page: int,
        per_page: int,
        status: MediaRequestStatus | None,
        media_type: MediaType | None,
    ) -> tuple[list[MediaRequestRecord], int]:
        """Return paginated media requests matching the provided filters."""

    async def create_request(self, data: CreateMediaRequestData) -> MediaRequestRecord:
        """Persist a new media request and return the stored record."""

    async def get_request(self, request_id: str) -> MediaRequestRecord | None:
        """Fetch a single media request by identifier."""

    async def update_request(
        self,
        request_id: str,
        data: UpdateMediaRequestData,
    ) -> MediaRequestRecord | None:
        """Update an existing media request and return the new state."""

    async def delete_request(self, request_id: str) -> bool:
        """Remove a media request. Returns True if a row was deleted."""


__all__ = [
    "CreateMediaRequestData",
    "MediaRequestRecord",
    "MediaRequestRepository",
    "UpdateMediaRequestData",
]
