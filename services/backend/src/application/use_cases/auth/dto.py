"""Output DTOs for auth use cases."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from src.application.interfaces.users import UserRecord


@dataclass(slots=True)
class IssuedSessionDTO:
    """A freshly issued (or rotated) session.

    ``refresh_token`` is the plaintext token; only its hash is ever persisted.
    The route is responsible for turning it into a cookie.
    """

    access_token: str
    refresh_token: str
    refresh_expires_at: datetime
    user: UserRecord


__all__ = ["IssuedSessionDTO"]
