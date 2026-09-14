"""Shared logic for minting an access token plus a new refresh token family."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from src.application.interfaces.auth import AccessTokenCodec, RefreshTokenRepository
from src.application.interfaces.users import UserRecord
from src.application.use_cases.auth.dto import IssuedSessionDTO
from src.application.utility.secret_tokens import generate_token, hash_token


class SessionIssuer:
    """Issues a session: one access token, one brand-new refresh token family."""

    def __init__(
        self,
        *,
        refresh_tokens: RefreshTokenRepository,
        access_tokens: AccessTokenCodec,
        access_token_ttl_seconds: int,
        session_ttl_seconds: int,
        remember_ttl_seconds: int,
    ) -> None:
        self._refresh_tokens = refresh_tokens
        self._access_tokens = access_tokens
        self._access_ttl = access_token_ttl_seconds
        self._session_ttl = session_ttl_seconds
        self._remember_ttl = remember_ttl_seconds

    async def issue(self, user: UserRecord, *, remember_me: bool) -> IssuedSessionDTO:
        return await self._issue(user, family_id=uuid.uuid4().hex, remember_me=remember_me)

    async def rotate(
        self, user: UserRecord, *, family_id: str, remember_me: bool
    ) -> IssuedSessionDTO:
        # Rotation keeps the family id so reuse of a stale token can revoke the
        # whole chain, and keeps the original remember-me duration.
        return await self._issue(user, family_id=family_id, remember_me=remember_me)

    async def _issue(
        self, user: UserRecord, *, family_id: str, remember_me: bool
    ) -> IssuedSessionDTO:
        ttl = self._remember_ttl if remember_me else self._session_ttl
        now = datetime.now(UTC)
        expires_at = now + timedelta(seconds=ttl)
        plaintext = generate_token()

        await self._refresh_tokens.store(
            id=uuid.uuid4().hex,
            user_id=user.id,
            family_id=family_id,
            token_hash=hash_token(plaintext),
            remember=remember_me,
            issued_at=now,
            expires_at=expires_at,
        )
        access_token = self._access_tokens.encode(
            subject=user.id,
            role=user.role.value,
            via="session",
            ttl_seconds=self._access_ttl,
        )
        return IssuedSessionDTO(
            access_token=access_token,
            refresh_token=plaintext,
            refresh_expires_at=expires_at,
            user=user,
        )


__all__ = ["SessionIssuer"]
