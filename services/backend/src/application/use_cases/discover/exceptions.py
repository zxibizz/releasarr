"""Custom exceptions for the add-request flow."""

from __future__ import annotations

from src.domain.enums import MediaType

# Each media type is served by one metadata provider and one *arr app, and the
# messages below name whichever of them the caller has to go and configure.
METADATA_PROVIDERS: dict[MediaType, tuple[str, str]] = {
    MediaType.SERIES: ("TVDB", "RELEASARR_TVDB_API_KEY"),
    MediaType.MOVIE: ("TMDB", "RELEASARR_TMDB_API_KEY"),
}

ARR_APPS: dict[MediaType, str] = {
    MediaType.SERIES: "Sonarr",
    MediaType.MOVIE: "Radarr",
}


class MetadataProviderUnavailableError(RuntimeError):
    """Raised when no metadata provider is configured for what was searched.

    A search across both media types names both providers, since configuring
    either one is enough to make it work.
    """

    def __init__(self, *media_types: MediaType) -> None:
        self.media_types = media_types
        settings = ", ".join(METADATA_PROVIDERS[media_type][1] for media_type in media_types)
        providers = " or ".join(METADATA_PROVIDERS[media_type][0] for media_type in media_types)
        searched = " or ".join(media_type.value for media_type in media_types)
        super().__init__(f"{providers} is not configured; set {settings} to search {searched}")


class MediaNotFoundError(LookupError):
    """Raised when the *arr app cannot resolve a metadata provider id."""

    def __init__(self, media_type: MediaType, provider_id: int) -> None:
        provider, _ = METADATA_PROVIDERS[media_type]
        app = ARR_APPS[media_type]
        super().__init__(f"{app} found no {media_type.value} for {provider} id {provider_id}")
        self.media_type = media_type
        self.provider_id = provider_id


class NoQualityProfileError(RuntimeError):
    """Raised when the *arr app reports no quality profile to add against."""

    def __init__(self, media_type: MediaType) -> None:
        super().__init__(f"{ARR_APPS[media_type]} has no quality profile configured")
        self.media_type = media_type


class InvalidRootFolderError(ValueError):
    """Raised when the requested root folder is not one the *arr app knows."""

    def __init__(self, root_folder_path: str) -> None:
        super().__init__(f"'{root_folder_path}' is not a configured root folder")
        self.root_folder_path = root_folder_path


class DisallowedRootFolderError(PermissionError):
    """Raised when a caller's allowed-folder list excludes the requested path."""

    def __init__(self, root_folder_path: str) -> None:
        super().__init__(f"'{root_folder_path}' is not permitted for this user")
        self.root_folder_path = root_folder_path


class SeasonSelectionError(ValueError):
    """Raised when the requested seasons do not fit the picked media."""


class SeasonsUnmanageableError(ValueError):
    """Raised when a request has no series in Sonarr whose seasons we could manage."""


__all__ = [
    "InvalidRootFolderError",
    "MediaNotFoundError",
    "MetadataProviderUnavailableError",
    "NoQualityProfileError",
    "SeasonSelectionError",
    "SeasonsUnmanageableError",
]
