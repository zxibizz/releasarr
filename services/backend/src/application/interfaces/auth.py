"""Interfaces supporting authentication: refresh tokens, service keys, and crypto ports."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(slots=True)
class RefreshTokenRecord:
    """A single refresh token in a rotation family."""

    id: str
    user_id: str
    family_id: str
    token_hash: str
    remember: bool
    issued_at: datetime
    expires_at: datetime
    revoked_at: datetime | None


class RefreshTokenRepository(Protocol):
    """Protocol describing persistence for refresh token rotation."""

    async def store(
        self,
        *,
        id: str,
        user_id: str,
        family_id: str,
        token_hash: str,
        remember: bool,
        issued_at: datetime,
        expires_at: datetime,
    ) -> RefreshTokenRecord:
        """Persist a newly issued refresh token."""

    async def get_by_hash(self, token_hash: str) -> RefreshTokenRecord | None:
        """Look up a refresh token by the hash of its plaintext."""

    async def revoke(self, token_id: str) -> None:
        """Mark a single token as revoked (used when rotating it)."""

    async def revoke_family(self, family_id: str) -> None:
        """Revoke every token in a rotation family (used on reuse or logout)."""

    async def purge_expired(self, *, now: datetime) -> int:
        """Delete tokens past their expiry. Returns the number removed."""


@dataclass(slots=True)
class ServiceApiKeyRecord:
    """The single service API key: always admin, never bound to a user, never hidden."""

    id: str
    key: str
    last_used_at: datetime | None
    created_at: datetime


class ServiceApiKeyRepository(Protocol):
    """Protocol describing persistence for the singleton service API key."""

    async def get(self) -> ServiceApiKeyRecord | None:
        """Fetch the current service key, if one has been created yet."""

    async def get_by_key(self, key: str) -> ServiceApiKeyRecord | None:
        """Look up the service key by its value."""

    async def replace(self, *, id: str, key: str) -> ServiceApiKeyRecord:
        """Replace the service key with a newly generated one, deleting any prior key."""

    async def touch_last_used(self, key_id: str, *, at: datetime) -> None:
        """Record that the key was just used to authenticate."""


class PasswordHasher(Protocol):
    """Port for password hashing, so use cases stay ignorant of the algorithm."""

    def hash(self, plaintext: str) -> str:
        """Hash a plaintext password."""

    def verify_and_update(self, plaintext: str, hashed: str) -> tuple[bool, str | None]:
        """Check a plaintext password against a stored hash.

        Returns ``(matched, new_hash)``; ``new_hash`` is set when the stored
        hash used outdated parameters and should be persisted.
        """

    def verify_dummy(self, plaintext: str) -> None:
        """Spend the time a real check would, when no such user exists.

        Keeps a login attempt against an unknown username indistinguishable, by
        timing, from one against a known username with the wrong password.
        """


@dataclass(slots=True)
class AccessTokenClaims:
    """Decoded claims from an access token."""

    subject: str
    role: str
    via: str
    issued_at: datetime
    expires_at: datetime


class AccessTokenCodec(Protocol):
    """Port for encoding/decoding short-lived access tokens."""

    def encode(self, *, subject: str, role: str, via: str, ttl_seconds: int) -> str:
        """Produce a signed access token."""

    def decode(self, token: str) -> AccessTokenClaims:
        """Validate and decode an access token, raising ``InvalidAccessTokenError``."""


__all__ = [
    "AccessTokenClaims",
    "AccessTokenCodec",
    "PasswordHasher",
    "RefreshTokenRecord",
    "RefreshTokenRepository",
    "ServiceApiKeyRecord",
    "ServiceApiKeyRepository",
]
