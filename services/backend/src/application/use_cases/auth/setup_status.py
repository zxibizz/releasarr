"""Whether first-run setup (creating the admin account) is still required."""

from __future__ import annotations

from src.application.interfaces.users import UserRepository


class GetSetupStatusUseCase:
    def __init__(self, *, users: UserRepository) -> None:
        self._users = users

    async def execute(self) -> bool:
        """Return True when no user exists yet and setup must run first."""

        return await self._users.count_users() == 0


__all__ = ["GetSetupStatusUseCase"]
