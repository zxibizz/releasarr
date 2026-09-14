"""Use cases for admin-managed service API keys (used by the future bot)."""

from __future__ import annotations

from uuid import uuid4

from src.application.interfaces.auth import ServiceApiKeyRecord, ServiceApiKeyRepository
from src.application.interfaces.users import UserRepository
from src.application.use_cases.users.commands import CreateServiceKeyCommand
from src.application.use_cases.users.exceptions import ServiceKeyNotFoundError, UserNotFoundError
from src.application.utility.secret_tokens import generate_service_key, hash_token


class CreateServiceKeyUseCase:
    """Create a service key and return it alongside its one-time plaintext."""

    def __init__(self, *, service_api_keys: ServiceApiKeyRepository, users: UserRepository) -> None:
        self._service_api_keys = service_api_keys
        self._users = users

    async def execute(self, command: CreateServiceKeyCommand) -> tuple[ServiceApiKeyRecord, str]:
        if await self._users.get_user(command.user_id) is None:
            raise UserNotFoundError(command.user_id)

        plaintext = generate_service_key()
        record = await self._service_api_keys.create_key(
            id=uuid4().hex,
            name=command.name,
            prefix=plaintext[:12],
            key_hash=hash_token(plaintext),
            user_id=command.user_id,
            can_impersonate=command.can_impersonate,
            expires_at=command.expires_at,
        )
        return record, plaintext


class ListServiceKeysUseCase:
    def __init__(self, *, service_api_keys: ServiceApiKeyRepository) -> None:
        self._service_api_keys = service_api_keys

    async def execute(self) -> list[ServiceApiKeyRecord]:
        return await self._service_api_keys.list_keys()


class RevokeServiceKeyUseCase:
    def __init__(self, *, service_api_keys: ServiceApiKeyRepository) -> None:
        self._service_api_keys = service_api_keys

    async def execute(self, key_id: str) -> None:
        if not await self._service_api_keys.delete_key(key_id):
            raise ServiceKeyNotFoundError(key_id)


__all__ = ["CreateServiceKeyUseCase", "ListServiceKeysUseCase", "RevokeServiceKeyUseCase"]
