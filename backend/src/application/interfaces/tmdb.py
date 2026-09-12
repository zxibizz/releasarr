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


class TmdbService(Protocol):
    """Protocol describing required TMDB operations."""

    async def get_movie(
        self,
        tmdb_id: int,
        languages: Sequence[str] | None = None,
    ) -> TmdbMovieMetadata:
        """Return localized metadata for a movie with optional language filtering."""


__all__ = ["TmdbMovieMetadata", "TmdbService", "TmdbTranslation"]
