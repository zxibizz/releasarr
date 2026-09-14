"""Revoke a session's refresh token family on logout."""

from __future__ import annotations

from src.application.interfaces.auth import RefreshTokenRepository
from src.application.utility.secret_tokens import hash_token


class LogoutUseCase:
    """Revoke the refresh token family behind a logout call.

    Idempotent: a missing or already-invalid cookie is not an error, since the
    end state either way is "no active session".
    """

    def __init__(self, *, refresh_tokens: RefreshTokenRepository) -> None:
        self._refresh_tokens = refresh_tokens

    async def execute(self, refresh_token: str | None) -> None:
        if not refresh_token:
            return
        record = await self._refresh_tokens.get_by_hash(hash_token(refresh_token))
        if record is not None:
            await self._refresh_tokens.revoke_family(record.family_id)


__all__ = ["LogoutUseCase"]
