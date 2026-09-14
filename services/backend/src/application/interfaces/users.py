"""Interfaces supporting user management."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol

from src.application.utility.sentinels import UNSET, _Unset
from src.domain.enums import UserRole


@dataclass(slots=True)
class UserRecord:
    """Normalized representation of a user account."""

    id: str
    username: str
    display_name: str | None
    password_hash: str
    role: UserRole
    is_active: bool
    can_view_all_requests: bool
    can_access_tasks: bool
    can_access_indexers: bool
    can_access_logs: bool
    allowed_root_folders: list[str]
    failed_login_attempts: int
    locked_until: datetime | None
    last_login_at: datetime | None
    created_at: datetime
    updated_at: datetime


@dataclass(slots=True)
class CreateUserData:
    """Payload required to persist a new user."""

    id: str
    username: str
    password_hash: str
    role: UserRole = UserRole.USER
    display_name: str | None = None
    is_active: bool = True
    can_view_all_requests: bool = False
    can_access_tasks: bool = False
    can_access_indexers: bool = False
    can_access_logs: bool = False
    allowed_root_folders: list[str] = field(default_factory=list)


@dataclass(slots=True)
class UpdateUserData:
    """Fields that may be updated on an existing user.

    Fields default to ``UNSET`` so the repository can distinguish an omitted
    field from an explicit value.
    """

    display_name: str | None | _Unset = UNSET
    password_hash: str | _Unset = UNSET
    role: UserRole | _Unset = UNSET
    is_active: bool | _Unset = UNSET
    can_view_all_requests: bool | _Unset = UNSET
    can_access_tasks: bool | _Unset = UNSET
    can_access_indexers: bool | _Unset = UNSET
    can_access_logs: bool | _Unset = UNSET
    allowed_root_folders: list[str] | _Unset = UNSET
    failed_login_attempts: int | _Unset = UNSET
    locked_until: datetime | None | _Unset = UNSET
    last_login_at: datetime | None | _Unset = UNSET


class UserRepository(Protocol):
    """Protocol describing persistence operations for user accounts."""

    async def list_users(self) -> list[UserRecord]:
        """Return every user, ordered by username."""

    async def count_users(self) -> int:
        """Return the total number of users. Used to gate first-run bootstrap."""

    async def get_user(self, user_id: str) -> UserRecord | None:
        """Fetch a single user by id."""

    async def get_by_username(self, username: str) -> UserRecord | None:
        """Fetch a single user by username (case-insensitive)."""

    async def create_user(self, data: CreateUserData) -> UserRecord:
        """Persist a new user and return the stored record."""

    async def update_user(self, user_id: str, data: UpdateUserData) -> UserRecord | None:
        """Apply a partial update to an existing user."""

    async def delete_user(self, user_id: str) -> bool:
        """Remove a user. Returns False if it did not exist."""


__all__ = [
    "CreateUserData",
    "UpdateUserData",
    "UserRecord",
    "UserRepository",
]
