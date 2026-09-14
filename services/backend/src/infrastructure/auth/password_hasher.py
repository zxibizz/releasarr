"""Argon2 password hashing via pwdlib."""

from __future__ import annotations

from pwdlib import PasswordHash

# A hash of a password nobody could have chosen. Verifying against it when a
# username is unknown keeps failed-login timing indistinguishable from a real
# mismatch, so the response does not leak which usernames exist.
_DUMMY_HASH = (
    "$argon2id$v=19$m=65536,t=3,p=4$"
    "AAAAAAAAAAAAAAAAAAAAAA$AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
)


class Argon2PasswordHasher:
    """Adapter implementing ``PasswordHasher`` over ``pwdlib``."""

    def __init__(self) -> None:
        self._hasher = PasswordHash.recommended()

    def hash(self, plaintext: str) -> str:
        return self._hasher.hash(plaintext)

    def verify_and_update(self, plaintext: str, hashed: str) -> tuple[bool, str | None]:
        return self._hasher.verify_and_update(plaintext, hashed)

    def verify_dummy(self, plaintext: str) -> None:
        """Spend the same time as a real check when no such user exists."""

        self._hasher.verify_and_update(plaintext, _DUMMY_HASH)


__all__ = ["Argon2PasswordHasher"]
