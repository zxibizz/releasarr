"""Interfaces supporting media request use cases."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol

from src.application.utility.sentinels import UNSET, _Unset
from src.domain.enums import MediaRequestStatus, MediaType


@dataclass(slots=True)
class MediaLocalization:
    """Localized title/overview pair for a specific language."""

    title: str | None = None
    overview: str | None = None


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
    sonarr_series_id: int | None = None
    radarr_movie_id: int | None = None
    localizations: dict[str, MediaLocalization] = field(default_factory=dict)


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
    sonarr_series_id: int | None = None
    radarr_movie_id: int | None = None
    localizations: dict[str, MediaLocalization] = field(default_factory=dict)


@dataclass(slots=True)
class UpdateMediaRequestData:
    """Fields that may be updated on an existing media request.

    Fields default to ``UNSET`` so the repository can distinguish an omitted
    field from an explicit ``None`` (which clears a nullable column).
    """

    title: str | None | _Unset = UNSET
    year: int | _Unset = UNSET
    poster_url: str | None | _Unset = UNSET
    overview: str | None | _Unset = UNSET
    genres: list[str] | _Unset = UNSET
    status: MediaRequestStatus | _Unset = UNSET
    runtime_minutes: int | None | _Unset = UNSET
    imdb_id: str | None | _Unset = UNSET
    season_number: int | None | _Unset = UNSET
    total_episodes: int | None | _Unset = UNSET
    series_title: str | None | _Unset = UNSET
    series_year: int | None | _Unset = UNSET
    sonarr_series_id: int | None | _Unset = UNSET
    radarr_movie_id: int | None | _Unset = UNSET
    localizations: dict[str, MediaLocalization] | _Unset = UNSET


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

    async def find_by_sonarr(
        self,
        *,
        sonarr_series_id: int,
        season_number: int,
    ) -> MediaRequestRecord | None:
        """Look up a Sonarr-backed request by series and season."""

    async def list_sonarr_requests(self) -> list[MediaRequestRecord]:
        """Return all requests linked to Sonarr series identifiers."""

    async def find_by_radarr(self, *, radarr_movie_id: int) -> MediaRequestRecord | None:
        """Look up a Radarr-backed request by movie identifier."""

    async def list_radarr_requests(self) -> list[MediaRequestRecord]:
        """Return all requests linked to Radarr movie identifiers."""


__all__ = [
    "CreateMediaRequestData",
    "MediaLocalization",
    "MediaRequestRecord",
    "MediaRequestRepository",
    "UpdateMediaRequestData",
]
