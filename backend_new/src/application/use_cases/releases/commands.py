"""Command objects consumed by release use cases."""

from __future__ import annotations

from dataclasses import dataclass

from src.domain.enums import ReleaseStatus


@dataclass(slots=True)
class ListReleasesOptions:
    page: int | None = None
    per_page: int | None = None
    status: ReleaseStatus | None = None
    request_id: str | None = None


@dataclass(slots=True)
class CreateReleaseCommand:
    magnet_link: str
    request_ids: list[str]


@dataclass(slots=True)
class FileMappingCommand:
    file_id: str
    mapping_type: str | None = None
    request_id: str | None = None
    request_title: str | None = None
    season: int | None = None
    episode: int | None = None


@dataclass(slots=True)
class UpdateFileMappingsCommand:
    release_id: str
    files: list[FileMappingCommand]


@dataclass(slots=True)
class ReleaseIdCommand:
    release_id: str


@dataclass(slots=True)
class SearchReleaseSourcesCommand:
    query: str
    request_id: str | None = None


@dataclass(slots=True)
class QueueReleaseDownloadCommand:
    request_id: str
    release_id: str


__all__ = [
    "CreateReleaseCommand",
    "FileMappingCommand",
    "ListReleasesOptions",
    "QueueReleaseDownloadCommand",
    "ReleaseIdCommand",
    "SearchReleaseSourcesCommand",
    "UpdateFileMappingsCommand",
]
