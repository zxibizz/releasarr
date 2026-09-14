"""Rotate a refresh token, detecting reuse of an already-rotated one."""

from __future__ import annotations

from datetime import UTC, datetime

from src.application.interfaces.auth import RefreshTokenRepository
from src.application.interfaces.users import UserRepository
from src.application.use_cases.auth.dto import IssuedSessionDTO
from src.application.use_cases.auth.exceptions import InvalidRefreshTokenError
from src.application.use_cases.auth.session_issuer import SessionIssuer
from src.application.utility.secret_tokens import hash_token


class RefreshSessionUseCase:
    """Exchange a refresh token cookie for a new access token and rotated cookie."""

    def __init__(
        self,
        *,
        users: UserRepository,
        refresh_tokens: RefreshTokenRepository,
        session_issuer: SessionIssuer,
    ) -> None:
        self._users = users
        self._refresh_tokens = refresh_tokens
        self._session_issuer = session_issuer

    async def execute(self, refresh_token: str) -> IssuedSessionDTO:
        record = await self._refresh_tokens.get_by_hash(hash_token(refresh_token))
        if record is None:
            raise InvalidRefreshTokenError()

        if record.revoked_at is not None:
            # This token was already rotated away; someone presenting it again
            # means the chain may be compromised, so the whole family is burned.
            await self._refresh_tokens.revoke_family(record.family_id)
            raise InvalidRefreshTokenError()

        if record.expires_at <= datetime.now(UTC):
            raise InvalidRefreshTokenError()

        user = await self._users.get_user(record.user_id)
        if user is None or not user.is_active:
            raise InvalidRefreshTokenError()

        await self._refresh_tokens.revoke(record.id)
        return await self._session_issuer.rotate(
            user, family_id=record.family_id, remember_me=record.remember
        )


__all__ = ["RefreshSessionUseCase"]
