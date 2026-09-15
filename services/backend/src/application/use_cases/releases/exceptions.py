"""Custom exceptions for release operations."""

from __future__ import annotations


class ReleaseNotFoundError(LookupError):
    """Raised when a release could not be located."""

    def __init__(self, release_id: str):
        message = f"Release '{release_id}' was not found"
        super().__init__(message)
        self.release_id = release_id


class ReleaseConflictError(RuntimeError):
    """Raised when attempting to create a release that already exists."""

    def __init__(self, release_id: str):
        message = f"Release '{release_id}' already exists"
        super().__init__(message)
        self.release_id = release_id


class ReleaseActionNotAllowedError(RuntimeError):
    """Raised when pause/resume operations are invalid for the current state."""

    def __init__(self, release_id: str, action: str):
        message = f"Release '{release_id}' cannot perform action '{action}'"
        super().__init__(message)
        self.release_id = release_id
        self.action = action


class ReleaseFileNotFoundError(LookupError):
    """Raised when a file referenced in a mapping update does not exist."""

    def __init__(self, release_id: str, file_id: str):
        message = f"File '{file_id}' was not found for release '{release_id}'"
        super().__init__(message)
        self.release_id = release_id
        self.file_id = file_id


class ReleaseDownloadConflictError(RuntimeError):
    """Raised when a release download cannot be queued due to conflicts."""

    def __init__(self, request_id: str, release_id: str):
        message = f"Download for release '{release_id}' and request '{request_id}' is not allowed"
        super().__init__(message)
        self.request_id = request_id
        self.release_id = release_id


class ReleaseDownloadFailedError(RuntimeError):
    """Raised when a release download fails unexpectedly."""

    def __init__(self, release_id: str, reason: str):
        message = f"Failed to download release '{release_id}': {reason}"
        super().__init__(message)
        self.release_id = release_id
        self.reason = reason


class ReleaseRegrabRejectedError(RuntimeError):
    """Raised when a replacement torrent cannot be trusted with a release's files.

    A re-grab rewrites the release row in place, so a replacement that does not
    carry every file the release already has would leave it describing files that
    are not there - and the export imports from exactly those paths. Nothing is
    queued or written when this is raised.
    """

    def __init__(self, release_id: str, missing_files: list[str]):
        message = (
            f"Replacement torrent for release '{release_id}' is missing "
            f"{len(missing_files)} file(s) the release already has"
        )
        super().__init__(message)
        self.release_id = release_id
        self.missing_files = missing_files


class ExistingReleasesDecisionRequiredError(RuntimeError):
    """Raised when a request already has releases and the caller did not say
    whether to keep or replace them."""

    def __init__(self, request_id: str, release_ids: list[str]):
        message = f"Request '{request_id}' already has releases; existing_releases is required"
        super().__init__(message)
        self.request_id = request_id
        self.release_ids = release_ids
        self.details = {"release_ids": release_ids}


class QbittorrentNotConfiguredError(RuntimeError):
    """Raised when an operation needs qBittorrent and no client is set up.

    The metadata providers are optional because a sync has something to fall back
    on. These operations do not: every one of them is about a torrent, so with no
    client there is nothing to queue, pause, resume or delete, and reporting
    success would be a lie rather than a degraded answer.
    """

    def __init__(self) -> None:
        super().__init__(
            "qBittorrent is not configured; set RELEASARR_QBITTORRENT_URL, "
            "RELEASARR_QBITTORRENT_USERNAME and RELEASARR_QBITTORRENT_PASSWORD"
        )


__all__ = [
    "ExistingReleasesDecisionRequiredError",
    "QbittorrentNotConfiguredError",
    "ReleaseActionNotAllowedError",
    "ReleaseConflictError",
    "ReleaseDownloadConflictError",
    "ReleaseDownloadFailedError",
    "ReleaseFileNotFoundError",
    "ReleaseNotFoundError",
]
