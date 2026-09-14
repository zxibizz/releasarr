"""Tests for the permission model: role bypass, flags, and request scope."""

from __future__ import annotations

from datetime import UTC, datetime

from src.application.interfaces.users import UserRecord
from src.application.use_cases.auth.permissions import (
    Permission,
    RequestScope,
    allowed_root_folders,
    has_permission,
)
from src.domain.enums import UserRole


def _make_user(**overrides: object) -> UserRecord:
    defaults: dict[str, object] = {
        "id": "u1",
        "username": "user",
        "display_name": None,
        "password_hash": "x",
        "role": UserRole.USER,
        "is_active": True,
        "can_view_all_requests": False,
        "can_access_tasks": False,
        "can_access_indexers": False,
        "can_access_logs": False,
        "allowed_root_folders": [],
        "failed_login_attempts": 0,
        "locked_until": None,
        "last_login_at": None,
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }
    defaults.update(overrides)
    return UserRecord(**defaults)  # type: ignore[arg-type]


def test_admin_bypasses_every_flag() -> None:
    admin = _make_user(role=UserRole.ADMIN)
    assert has_permission(admin, Permission.TASKS)
    assert has_permission(admin, Permission.MANAGE_USERS)
    assert allowed_root_folders(admin) is None


def test_manage_users_is_admin_only_regardless_of_flags() -> None:
    user = _make_user(can_access_tasks=True, can_access_logs=True)
    assert not has_permission(user, Permission.MANAGE_USERS)


def test_flags_gate_individual_permissions() -> None:
    user = _make_user(can_access_tasks=True)
    assert has_permission(user, Permission.TASKS)
    assert not has_permission(user, Permission.LOGS)


def test_empty_allowed_root_folders_means_unrestricted() -> None:
    user = _make_user(allowed_root_folders=[])
    assert allowed_root_folders(user) is None


def test_populated_allowed_root_folders_are_returned_verbatim() -> None:
    user = _make_user(allowed_root_folders=["/movies"])
    assert allowed_root_folders(user) == ["/movies"]


def test_scope_for_user_without_view_all_is_restricted_to_self() -> None:
    user = _make_user()
    scope = RequestScope.for_user(user)
    assert scope.is_restricted
    assert scope.permits(user.id)
    assert not scope.permits("someone-else")
    assert not scope.permits(None)


def test_scope_for_user_with_view_all_is_unrestricted() -> None:
    user = _make_user(can_view_all_requests=True)
    scope = RequestScope.for_user(user)
    assert not scope.is_restricted
    assert scope.permits(None)
    assert scope.permits("anyone")
