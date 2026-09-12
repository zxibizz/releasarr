"""Interfaces for interacting with Radarr services."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(slots=True)
class MovieDetails:
    """Detailed information about a Radarr movie."""

    id: int
    title: str
    year: int | None
    overview: str | None
    poster_url: str | None
    imdb_id: str | None
    tmdb_id: int | None
    genres: list[str] = field(default_factory=list)
    runtime_minutes: int | None = None
    has_file: bool = False


@dataclass(slots=True)
class MovieImportFile:
    """File details for Radarr's manual import command."""

    path: str
    movie_id: int
    folder_name: str


class RadarrService(Protocol):
    """Protocol describing the subset of Radarr operations we rely on."""

    async def get_missing_movies(self) -> list[MovieDetails]:
        """Return monitored Radarr movies that are still missing a file."""

    async def get_movie(self, movie_id: int) -> MovieDetails:
        """Return detailed information for a single Radarr movie."""

    async def manual_import(self, files: list[MovieImportFile]) -> bool:
        """Trigger a manual import command for the designated files."""


__all__ = [
    "MovieDetails",
    "MovieImportFile",
    "RadarrService",
]
