"""Interfaces for interacting with the TMDB metadata service."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol


@dataclass(slots=True)
class TmdbTranslation:
    """Localized title and overview information."""

    language: str
    title: str | None = None
    overview: str | None = None


@dataclass(slots=True)
class TmdbMovieMetadata:
    """Metadata returned for a TMDB movie lookup."""

    tmdb_id: int
    translations: dict[str, TmdbTranslation]


@dataclass(slots=True)
class TmdbSearchResult:
    """A single movie match returned by a TMDB title search."""

    tmdb_id: int
    title: str
    year: int | None = None
    overview: str | None = None
    poster_url: str | None = None
    # ``title`` is localized, so a term typed in another language may match none
    # of it. Ranking scores every title TMDB knows for the entry instead.
    match_titles: tuple[str, ...] = ()
    # How many ratings the movie accumulated on TMDB. Only ever compared against
    # the other hits of the same search; TMDB counts votes in the hundreds where
    # TVDB counts followers in the millions.
    popularity: int = 0


class TmdbService(Protocol):
    """Protocol describing required TMDB operations."""

    async def get_movie(
        self,
        tmdb_id: int,
        languages: Sequence[str] | None = None,
    ) -> TmdbMovieMetadata:
        """Return localized metadata for a movie with optional language filtering."""

    async def search_movies(
        self,
        query: str,
        limit: int = 20,
        languages: Sequence[str] | None = None,
    ) -> list[TmdbSearchResult]:
        """Return movies matching a free-text query."""


__all__ = [
    "TmdbMovieMetadata",
    "TmdbSearchResult",
    "TmdbService",
    "TmdbTranslation",
]
