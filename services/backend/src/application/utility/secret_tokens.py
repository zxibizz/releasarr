"""Opaque secret tokens shared by refresh tokens and service API keys.

Pure stdlib logic (no framework dependency), so it can be used directly by
application-layer use cases without reaching into ``infrastructure/``.
"""

from __future__ import annotations

import hashlib
import secrets

# service keys are prefixed so they are recognisable (and greppable) in logs
# and config without ever revealing enough of the secret to reuse it.
SERVICE_KEY_PREFIX = "rlsr_"


def generate_token(*, n_bytes: int = 48) -> str:
    """Generate a URL-safe opaque token."""

    return secrets.token_urlsafe(n_bytes)


def generate_service_key() -> str:
    """Generate a service API key with a recognisable prefix."""

    return f"{SERVICE_KEY_PREFIX}{generate_token(n_bytes=32)}"


def hash_token(token: str) -> str:
    """Hash a token for storage. Lookups compare hashes, never plaintext."""

    return hashlib.sha256(token.encode("utf-8")).hexdigest()


__all__ = ["SERVICE_KEY_PREFIX", "generate_service_key", "generate_token", "hash_token"]
