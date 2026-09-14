"""Schemas for user account and service API key management."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import Field, field_serializer

from src.schemas.base import APIModel
from src.schemas.enums import UserRole


def _to_utc_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:  # default to UTC when the database returns naive values
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


class User(APIModel):
    id: str
    username: str
    display_name: str | None = None
    role: UserRole
    is_active: bool
    can_view_all_requests: bool
    can_access_tasks: bool
    can_access_indexers: bool
    can_access_logs: bool
    allowed_root_folders: list[str] = Field(default_factory=list)
    last_login_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    @field_serializer("last_login_at", "created_at", "updated_at")
    def _serialize_datetime(self, value: datetime | None) -> str | None:
        return _to_utc_iso(value)


class SessionUser(User):
    """The authenticated caller's own profile, as returned by ``GET /auth/me``."""


class UsersResponse(APIModel):
    users: list[User]


class CreateUserPayload(APIModel):
    username: str
    password: str
    display_name: str | None = None
    role: UserRole = UserRole.USER
    is_active: bool = True
    can_view_all_requests: bool = False
    can_access_tasks: bool = False
    can_access_indexers: bool = False
    can_access_logs: bool = False
    allowed_root_folders: list[str] = Field(default_factory=list)


class UpdateUserPayload(APIModel):
    display_name: str | None = None
    password: str | None = None
    role: UserRole | None = None
    is_active: bool | None = None
    can_view_all_requests: bool | None = None
    can_access_tasks: bool | None = None
    can_access_indexers: bool | None = None
    can_access_logs: bool | None = None
    allowed_root_folders: list[str] | None = None


class ChangePasswordPayload(APIModel):
    current_password: str
    new_password: str


__all__ = [
    "ChangePasswordPayload",
    "CreateUserPayload",
    "SessionUser",
    "UpdateUserPayload",
    "User",
    "UsersResponse",
]
