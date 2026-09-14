"""Resolve who is calling: a bearer access token, or a service API key."""

from __future__ import annotations

from datetime import UTC, datetime

from src.application.interfaces.auth import AccessTokenCodec, ServiceApiKeyRepository
from src.application.interfaces.users import UserRepository
from src.application.use_cases.auth.exceptions import (
    ImpersonationNotAllowedError,
    InactiveUserError,
    InvalidAccessTokenError,
)
from src.application.use_cases.auth.permissions import Principal
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

    async def authenticate_service_key(self, key: str, *, act_as_username: str | None) -> Principal:
        record = await self._service_api_keys.get_by_hash(hash_token(key))
        if record is None or not record.is_active:
            raise InvalidAccessTokenError()
        if record.expires_at is not None and record.expires_at <= datetime.now(UTC):
            raise InvalidAccessTokenError()

        target_user_id = record.user_id
        if act_as_username:
            if not record.can_impersonate:
                raise ImpersonationNotAllowedError()
            target = await self._users.get_by_username(act_as_username)
            if target is None:
                raise InvalidAccessTokenError()
            target_user_id = target.id

        user = await self._users.get_user(target_user_id)
        if user is None:
            raise InvalidAccessTokenError()
        if not user.is_active:
            raise InactiveUserError()

        await self._service_api_keys.touch_last_used(record.id, at=datetime.now(UTC))
        return Principal(user=user, via="service")


__all__ = ["AuthenticatePrincipalUseCase"]
