"""JWT access tokens via PyJWT."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt

from src.application.interfaces.auth import AccessTokenClaims
from src.application.use_cases.auth.exceptions import InvalidAccessTokenError

_ALGORITHM = "HS256"


class JwtAccessTokenCodec:
    """Adapter implementing ``AccessTokenCodec`` over PyJWT."""

    def __init__(self, secret: str) -> None:
        self._secret = secret

    def encode(self, *, subject: str, role: str, via: str, ttl_seconds: int) -> str:
        now = datetime.now(UTC)
        payload = {
            "sub": subject,
            "role": role,
            "via": via,
            "iat": now,
            "exp": now + timedelta(seconds=ttl_seconds),
        }
        return jwt.encode(payload, self._secret, algorithm=_ALGORITHM)

    def decode(self, token: str) -> AccessTokenClaims:
        try:
            payload = jwt.decode(token, self._secret, algorithms=[_ALGORITHM])
        except jwt.PyJWTError as exc:
            raise InvalidAccessTokenError() from exc

        try:
            return AccessTokenClaims(
                subject=payload["sub"],
                role=payload["role"],
                via=payload["via"],
                issued_at=datetime.fromtimestamp(payload["iat"], tz=UTC),
                expires_at=datetime.fromtimestamp(payload["exp"], tz=UTC),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise InvalidAccessTokenError() from exc


__all__ = ["JwtAccessTokenCodec"]
