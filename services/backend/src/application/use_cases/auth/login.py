"""Authenticate a username/password pair and issue a new session."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from src.application.interfaces.auth import PasswordHasher
from src.application.interfaces.users import UpdateUserData, UserRecord, UserRepository
from src.application.use_cases.auth.commands import LoginCommand
from src.application.use_cases.auth.dto import IssuedSessionDTO
from src.application.use_cases.auth.exceptions import (
    AccountLockedError,
    InactiveUserError,
    InvalidCredentialsError,
)
from src.application.use_cases.auth.session_issuer import SessionIssuer
from src.core.logging import get_logger
from src.domain.enums import LogComponent

_logger = get_logger(LogComponent.USECASE_AUTH)


class LoginUseCase:
    """Verify credentials, track failed attempts, and issue a session on success."""

    def __init__(
        self,
        *,
        users: UserRepository,
        password_hasher: PasswordHasher,
        session_issuer: SessionIssuer,
        max_failed_logins: int,
        lockout_seconds: int,
    ) -> None:
        self._users = users
        self._password_hasher = password_hasher
        self._session_issuer = session_issuer
        self._max_failed_logins = max_failed_logins
        self._lockout_seconds = lockout_seconds

    async def execute(self, command: LoginCommand) -> IssuedSessionDTO:
        user = await self._users.get_by_username(command.username)
        if user is None:
            # Spends the same time a real mismatch would, so the response does
            # not reveal whether the username exists.
            self._password_hasher.verify_dummy(command.password)
            raise InvalidCredentialsError()

        now = datetime.now(UTC)
        if user.locked_until is not None and user.locked_until > now:
            raise AccountLockedError(int((user.locked_until - now).total_seconds()))

        matched, new_hash = self._password_hasher.verify_and_update(
            command.password, user.password_hash
        )
        if not matched:
            await self._record_failed_login(user)
            raise InvalidCredentialsError()

        if not user.is_active:
            raise InactiveUserError()

        update = UpdateUserData(failed_login_attempts=0, locked_until=None, last_login_at=now)
        if new_hash is not None:
            update.password_hash = new_hash
        updated = await self._users.update_user(user.id, update)
        assert updated is not None  # the row was just read inside this call

        _logger.info("User logged in", username=user.username)
        return await self._session_issuer.issue(updated, remember_me=command.remember_me)

    async def _record_failed_login(self, user: UserRecord) -> None:
        attempts = user.failed_login_attempts + 1
        update = UpdateUserData(failed_login_attempts=attempts)
        if attempts >= self._max_failed_logins:
            update.locked_until = datetime.now(UTC) + timedelta(seconds=self._lockout_seconds)
            _logger.warning(
                "Account locked after repeated failed logins",
                username=user.username,
                attempts=attempts,
            )
        await self._users.update_user(user.id, update)


__all__ = ["LoginUseCase"]
