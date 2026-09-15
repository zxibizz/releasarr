"""Rotate a refresh token, detecting reuse of an already-rotated one."""

from __future__ import annotations

from datetime import UTC, datetime

from src.application.interfaces.auth import RefreshTokenRecord, RefreshTokenRepository
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
        reuse_grace_seconds: int = 0,
    ) -> None:
        self._users = users
        self._refresh_tokens = refresh_tokens
        self._session_issuer = session_issuer
        self._reuse_grace_seconds = reuse_grace_seconds

    async def execute(self, refresh_token: str) -> IssuedSessionDTO:
        now = datetime.now(UTC)
        record = await self._refresh_tokens.get_by_hash(hash_token(refresh_token))
        if record is None:
            raise InvalidRefreshTokenError()

        racing = await self._is_racing_rotation(record, now=now)
        if record.revoked_at is not None and not racing:
            # This token was rotated away already and has come back. Outside the
            # grace window below that means the chain may be compromised, so the
            # whole family is burned.
            await self._refresh_tokens.revoke_family(record.family_id)
            raise InvalidRefreshTokenError()

        if record.expires_at <= now:
            raise InvalidRefreshTokenError()

        user = await self._users.get_user(record.user_id)
        if user is None or not user.is_active:
            raise InvalidRefreshTokenError()

        if not racing:
            await self._refresh_tokens.revoke(record.id)
        return await self._session_issuer.rotate(
            user, family_id=record.family_id, remember_me=record.remember
        )

    async def _is_racing_rotation(self, record: RefreshTokenRecord, *, now: datetime) -> bool:
        """Whether a revoked token is a client racing itself rather than a replay.

        One browser shares a single refresh cookie between its tabs, and two
        requests can be sent with it before either response replaces it — so the
        loser arrives carrying the token the winner just rotated away. That is
        indistinguishable from theft only by timing: a real replay turns up once
        the family is no longer usable, so a recent rotation whose chain is
        still live is forgiven and rotated again.
        """

        if record.revoked_at is None:
            return False
        if (now - record.revoked_at).total_seconds() > self._reuse_grace_seconds:
            return False
        return await self._refresh_tokens.has_live_token(record.family_id, now=now)


__all__ = ["RefreshSessionUseCase"]
