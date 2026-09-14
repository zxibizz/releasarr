"""Resolve who is calling: a bearer access token, or the service API key."""

from __future__ import annotations

from datetime import UTC, datetime

from src.application.interfaces.auth import AccessTokenCodec, ServiceApiKeyRepository
from src.application.interfaces.users import UserRepository
from src.application.use_cases.auth.exceptions import InactiveUserError, InvalidAccessTokenError
from src.application.use_cases.auth.permissions import Principal, build_service_principal
from src.application.utility.secret_tokens import hash_token


class AuthenticatePrincipalUseCase:
    """Turn raw credentials from a request into a ``Principal``."""

    def __init__(
        self,
        *,
        users: UserRepository,
        service_api_keys: ServiceApiKeyRepository,
        access_tokens: AccessTokenCodec,
    ) -> None:
        self._users = users
        self._service_api_keys = service_api_keys
        self._access_tokens = access_tokens

    async def authenticate_bearer(self, token: str) -> Principal:
        claims = self._access_tokens.decode(token)
        user = await self._users.get_user(claims.subject)
        if user is None:
            raise InvalidAccessTokenError()
        if not user.is_active:
            raise InactiveUserError()
        return Principal(user=user, via="session")

    async def authenticate_service_key(self, key: str) -> Principal:
        record = await self._service_api_keys.get_by_hash(hash_token(key))
        if record is None:
            raise InvalidAccessTokenError()

        await self._service_api_keys.touch_last_used(record.id, at=datetime.now(UTC))
        return build_service_principal()


__all__ = ["AuthenticatePrincipalUseCase"]
