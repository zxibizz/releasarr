"""Custom exceptions for media request operations."""

from __future__ import annotations


class MediaRequestNotFoundError(LookupError):
    """Raised when a requested media request record is missing."""

    def __init__(self, request_id: str):
        message = f"Media request '{request_id}' was not found"
        super().__init__(message)
        self.request_id = request_id


class EmptyUpdatePayloadError(ValueError):
    """Raised when an update payload contains no actionable fields."""

    def __init__(self) -> None:
        super().__init__("No fields supplied for update")


__all__ = ["EmptyUpdatePayloadError", "MediaRequestNotFoundError"]
