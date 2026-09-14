"""First-run bootstrap: create the sole admin account before any other login works."""

from __future__ import annotations

from uuid import uuid4

from src.application.interfaces.auth import PasswordHasher
from src.application.interfaces.users import CreateUserData, UserRepository
from src.application.use_cases.auth.commands import BootstrapAdminCommand
from src.application.use_cases.auth.dto import IssuedSessionDTO
from src.application.use_cases.auth.exceptions import SetupAlreadyCompletedError
from src.application.use_cases.auth.session_issuer import SessionIssuer
from src.domain.enums import UserRole


class BootstrapAdminUseCase:
    """Create the first admin account, and only the first.

    Guarded by a count rather than a flag so it self-heals: a user deleted
    down to zero rows re-opens the door rather than staying locked out.
    """

    def __init__(
        self,
        *,
        users: UserRepository,
        password_hasher: PasswordHasher,
        session_issuer: SessionIssuer,
    ) -> None:
        self._users = users
        self._password_hasher = password_hasher
        self._session_issuer = session_issuer

    async def execute(self, command: BootstrapAdminCommand) -> IssuedSessionDTO:
        if await self._users.count_users() > 0:
            raise SetupAlreadyCompletedError()

        user = await self._users.create_user(
            CreateUserData(
                id=uuid4().hex,
                username=command.username,
                password_hash=self._password_hasher.hash(command.password),
                role=UserRole.ADMIN,
                display_name=command.display_name,
                is_active=True,
                can_view_all_requests=True,
                can_access_tasks=True,
                can_access_indexers=True,
                can_access_logs=True,
            )
        )
        return await self._session_issuer.issue(user, remember_me=True)


__all__ = ["BootstrapAdminUseCase"]
