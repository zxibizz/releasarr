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


class TvdbService(Protocol):
    """Protocol describing required TVDB operations."""

    async def get_series(
        self,
        tvdb_id: int,
        languages: Sequence[str] | None = None,
    ) -> TvdbSeriesMetadata:
        """Return detailed metadata for a series with optional language filtering."""


__all__ = ["TvdbSeriesMetadata", "TvdbService", "TvdbTranslation"]
