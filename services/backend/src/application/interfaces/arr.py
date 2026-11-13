"""Interfaces shared by the Sonarr and Radarr services.

Both apps expose the same library-management resources under the same shapes, so
the root folder and quality profile records live here rather than being spelled
out twice.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class ArrRootFolder:
    """A library location configured in Sonarr or Radarr."""

    path: str
    free_space: int | None = None
    accessible: bool = True


@dataclass(slots=True)
class ArrQualityProfile:
    """A quality profile configured in Sonarr or Radarr."""

    id: int
    name: str


@dataclass(slots=True)
class ArrImportEvent:
    """One import as Sonarr's or Radarr's history records it.

    ``target_id`` is the episode or the movie, ``file_id`` the episode or movie
    file the import created, and ``source_path`` the path it was imported from.
    """

    target_id: int
    file_id: int
    source_path: str
    date: datetime


__all__ = ["ArrImportEvent", "ArrQualityProfile", "ArrRootFolder"]
