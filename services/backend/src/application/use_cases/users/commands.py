"""Input commands for user and service-key management use cases."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from src.application.utility.sentinels import UNSET, _Unset
from src.domain.enums import UserRole


@dataclass(slots=True)
class CreateUserCommand:
    username: str
    password: str
    role: UserRole = UserRole.USER
    display_name: str | None = None
    is_active: bool = True
    can_view_all_requests: bool = False
    can_access_tasks: bool = False
    can_access_indexers: bool = False
    can_access_logs: bool = False
    allowed_root_folders: list[str] = field(default_factory=list)


@dataclass(slots=True)
class UpdateUserCommand:
    """Fields default to ``UNSET`` to distinguish "omitted" from "cleared"."""

    display_name: str | None | _Unset = UNSET
    password: str | _Unset = UNSET
    role: UserRole | _Unset = UNSET
    is_active: bool | _Unset = UNSET
    can_view_all_requests: bool | _Unset = UNSET
    can_access_tasks: bool | _Unset = UNSET
    can_access_indexers: bool | _Unset = UNSET
    can_access_logs: bool | _Unset = UNSET
    allowed_root_folders: list[str] | _Unset = UNSET


@dataclass(slots=True)
class ChangePasswordCommand:
    current_password: str
    new_password: str


@dataclass(slots=True)
class CreateServiceKeyCommand:
    name: str
    user_id: str
    can_impersonate: bool = False
    expires_at: datetime | None = None


__all__ = [
    "ChangePasswordCommand",
    "CreateServiceKeyCommand",
    "CreateUserCommand",
    "UpdateUserCommand",
]
