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


__all__ = [
    "ReleaseActionNotAllowedError",
    "ReleaseConflictError",
    "ReleaseDownloadConflictError",
    "ReleaseFileNotFoundError",
    "ReleaseNotFoundError",
]
