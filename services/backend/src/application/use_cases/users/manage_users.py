"""CRUD use cases for user accounts.

Grouped in one module because each operation is a handful of lines around the
same repository and the same last-admin guard; splitting them into one file
apiece would scatter that guard rather than clarify anything.
"""

from __future__ import annotations

from uuid import uuid4

from src.application.interfaces.auth import PasswordHasher
from src.application.interfaces.users import (
    CreateUserData,
    UpdateUserData,
    UserRecord,
    UserRepository,
)
from src.application.use_cases.auth.exceptions import InvalidCredentialsError
from src.application.use_cases.users.commands import (
    ChangePasswordCommand,
    CreateUserCommand,
    UpdateUserCommand,
)
from src.application.use_cases.users.exceptions import (
    LastAdminError,
    UsernameTakenError,
    UserNotFoundError,
)
from src.application.utility.sentinels import UNSET
from src.core.logging import get_logger
from src.domain.enums import LogComponent, UserRole

_logger = get_logger(LogComponent.USECASE_USERS)


async def _remaining_active_admins(
    users: UserRepository, excluding_user_id: str
) -> list[UserRecord]:
    return [
        user
        for user in await users.list_users()
        if user.id != excluding_user_id and user.role is UserRole.ADMIN and user.is_active
    ]


async def _guard_last_admin(
    users: UserRepository, target: UserRecord, command: UpdateUserCommand
) -> None:
    """Refuse an update that would leave no active admin behind."""

    if target.role is not UserRole.ADMIN:
        return
    demoting = command.role is not UNSET and command.role != UserRole.ADMIN
    deactivating = command.is_active is False
    if not (demoting or deactivating):
        return
    if not await _remaining_active_admins(users, target.id):
        raise LastAdminError()


class ListUsersUseCase:
    def __init__(self, *, users: UserRepository) -> None:
        self._users = users

    async def execute(self) -> list[UserRecord]:
        return await self._users.list_users()


class GetUserUseCase:
    def __init__(self, *, users: UserRepository) -> None:
        self._users = users

    async def execute(self, user_id: str) -> UserRecord:
        user = await self._users.get_user(user_id)
        if user is None:
            raise UserNotFoundError(user_id)
        return user


class CreateUserUseCase:
    def __init__(self, *, users: UserRepository, password_hasher: PasswordHasher) -> None:
        self._users = users
        self._password_hasher = password_hasher

    async def execute(self, command: CreateUserCommand) -> UserRecord:
        if await self._users.get_by_username(command.username) is not None:
            raise UsernameTakenError(command.username)

        user = await self._users.create_user(
            CreateUserData(
                id=uuid4().hex,
                username=command.username,
                password_hash=self._password_hasher.hash(command.password),
                role=command.role,
                display_name=command.display_name,
                is_active=command.is_active,
                can_view_all_requests=command.can_view_all_requests,
                can_access_tasks=command.can_access_tasks,
                can_access_indexers=command.can_access_indexers,
                can_access_logs=command.can_access_logs,
                allowed_root_folders=list(command.allowed_root_folders),
            )
        )
        _logger.info("User created", username=user.username, role=user.role.value)
        return user


class UpdateUserUseCase:
    def __init__(self, *, users: UserRepository, password_hasher: PasswordHasher) -> None:
        self._users = users
        self._password_hasher = password_hasher

    async def execute(self, user_id: str, command: UpdateUserCommand) -> UserRecord:
        target = await self._users.get_user(user_id)
        if target is None:
            raise UserNotFoundError(user_id)

        await _guard_last_admin(self._users, target, command)

        update = UpdateUserData(
            display_name=command.display_name,
            role=command.role,
            is_active=command.is_active,
            can_view_all_requests=command.can_view_all_requests,
            can_access_tasks=command.can_access_tasks,
            can_access_indexers=command.can_access_indexers,
            can_access_logs=command.can_access_logs,
            allowed_root_folders=command.allowed_root_folders,
        )
        if command.password is not UNSET:
            update.password_hash = self._password_hasher.hash(command.password)

        updated = await self._users.update_user(user_id, update)
        assert updated is not None  # the row was just read inside this call
        return updated


class DeleteUserUseCase:
    def __init__(self, *, users: UserRepository) -> None:
        self._users = users

    async def execute(self, user_id: str) -> None:
        target = await self._users.get_user(user_id)
        if target is None:
            raise UserNotFoundError(user_id)

        if target.role is UserRole.ADMIN and not await _remaining_active_admins(
            self._users, target.id
        ):
            raise LastAdminError()

        await self._users.delete_user(user_id)
        _logger.info("User deleted", username=target.username)


class ChangePasswordUseCase:
    """Self-service password change: requires the current password."""

    def __init__(self, *, users: UserRepository, password_hasher: PasswordHasher) -> None:
        self._users = users
        self._password_hasher = password_hasher

    async def execute(self, user_id: str, command: ChangePasswordCommand) -> None:
        user = await self._users.get_user(user_id)
        if user is None:
            raise UserNotFoundError(user_id)

        matched, _ = self._password_hasher.verify_and_update(
            command.current_password, user.password_hash
        )
        if not matched:
            raise InvalidCredentialsError()

        await self._users.update_user(
            user_id, UpdateUserData(password_hash=self._password_hasher.hash(command.new_password))
        )


__all__ = [
    "ChangePasswordUseCase",
    "CreateUserUseCase",
    "DeleteUserUseCase",
    "GetUserUseCase",
    "ListUsersUseCase",
    "UpdateUserUseCase",
]
