"""Permission model: a flat role plus per-user flags, and the request scope it implies."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from src.application.interfaces.users import UserRecord
from src.domain.enums import UserRole


class Permission(str, Enum):
    """A capability a user may or may not have, independent of their role."""

    VIEW_ALL_REQUESTS = "view_all_requests"
    TASKS = "tasks"
    INDEXERS = "indexers"
    LOGS = "logs"
    MANAGE_USERS = "manage_users"


_FLAG_ATTRS: dict[Permission, str] = {
    Permission.VIEW_ALL_REQUESTS: "can_view_all_requests",
    Permission.TASKS: "can_access_tasks",
    Permission.INDEXERS: "can_access_indexers",
    Permission.LOGS: "can_access_logs",
}


def has_permission(user: UserRecord, permission: Permission) -> bool:
    """Whether ``user`` may exercise ``permission``. Admins bypass every flag."""

    if user.role is UserRole.ADMIN:
        return True
    if permission is Permission.MANAGE_USERS:
        return False
    return bool(getattr(user, _FLAG_ATTRS[permission]))


def allowed_root_folders(user: UserRecord) -> list[str] | None:
    """Root folder paths ``user`` may add to. ``None`` means unrestricted."""

    if user.role is UserRole.ADMIN or not user.allowed_root_folders:
        return None
    return list(user.allowed_root_folders)


@dataclass(slots=True, frozen=True)
class RequestScope:
    """Which media requests a caller may see.

    ``owner_user_id`` set means restricted to that owner; ``None`` means every
    request, including ones with no owner at all.
    """

    owner_user_id: str | None = None

    @classmethod
    def unrestricted(cls) -> RequestScope:
        return cls(owner_user_id=None)

    @classmethod
    def owned_by(cls, user_id: str) -> RequestScope:
        return cls(owner_user_id=user_id)

    @property
    def is_restricted(self) -> bool:
        return self.owner_user_id is not None

    def permits(self, owner_user_id: str | None) -> bool:
        """Whether a request owned by ``owner_user_id`` is visible in this scope."""

        return not self.is_restricted or owner_user_id == self.owner_user_id

    @classmethod
    def for_user(cls, user: UserRecord) -> RequestScope:
        if has_permission(user, Permission.VIEW_ALL_REQUESTS):
            return cls.unrestricted()
        return cls.owned_by(user.id)


@dataclass(slots=True, frozen=True)
class Principal:
    """The authenticated caller behind a request: a user, and how they got in."""

    user: UserRecord
    via: str  # "session" (browser login) | "service" (a service API key)

    def has(self, permission: Permission) -> bool:
        return has_permission(self.user, permission)

    @property
    def is_admin(self) -> bool:
        return self.user.role is UserRole.ADMIN

    @property
    def scope(self) -> RequestScope:
        return RequestScope.for_user(self.user)


__all__ = [
    "Permission",
    "Principal",
    "RequestScope",
    "allowed_root_folders",
    "has_permission",
]
