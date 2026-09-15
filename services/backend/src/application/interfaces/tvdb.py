"""Interfaces for interacting with the TVDB metadata service."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Protocol


@dataclass(slots=True)
class TvdbTranslation:
    """Localized title and overview information."""

    language: str
    title: str | None = None
    overview: str | None = None
    season_overviews: dict[int, str | None] = field(default_factory=dict)


@dataclass(slots=True)
class TvdbSeriesMetadata:
    """Metadata returned for a TVDB series lookup."""

    tvdb_id: int
    name: str | None
    overview: str | None
    image_url: str | None
    year: int | None
    genres: list[str]
    translations: dict[str, TvdbTranslation]
    seasons: list[int] = field(default_factory=list)


@dataclass(slots=True)
class TvdbSearchResult:
    """A single series match returned by a TVDB title search."""

    tvdb_id: int
    name: str
    year: int | None = None
    overview: str | None = None
    image_url: str | None = None
    # ``name`` is whichever translation the caller's languages selected, so a
    # term typed in another language may match none of it. Ranking scores every
    # title TVDB knows for the entry instead.
    match_titles: tuple[str, ...] = ()
    # How many people follow the series on TVDB. Only ever compared against the
    # other hits of the same search: the scale is the provider's own, and the
    # adapter substitutes a weaker proxy when TVDB will not report followers.
    popularity: int = 0


class TvdbService(Protocol):
    """Protocol describing required TVDB operations."""

    @property
    def is_configured(self) -> bool:
        """Whether an API token is set. The base URL always has a default."""

    async def get_series(
        self,
        tvdb_id: int,
        languages: Sequence[str] | None = None,
    ) -> TvdbSeriesMetadata:
        """Return detailed metadata for a series with optional language filtering."""

    async def search_series(
        self,
        query: str,
        limit: int = 20,
        languages: Sequence[str] | None = None,
    ) -> list[TvdbSearchResult]:
        """Return series matching a free-text query."""


__all__ = [
    "TvdbSearchResult",
    "TvdbSeriesMetadata",
    "TvdbService",
    "TvdbTranslation",
]
