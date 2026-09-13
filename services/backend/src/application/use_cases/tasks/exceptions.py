"""Custom exceptions for sync job operations."""

from __future__ import annotations


class SyncJobNotFoundError(LookupError):
    """Raised when a sync job could not be located."""

    def __init__(self, job_id: str):
        message = f"Sync job '{job_id}' was not found"
        super().__init__(message)
        self.job_id = job_id


__all__ = ["SyncJobNotFoundError"]
