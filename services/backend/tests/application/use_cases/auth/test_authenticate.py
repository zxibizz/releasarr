"""Tests for resolving a Principal from bearer tokens and the service API key."""

from __future__ import annotations

import pytest

from src.application.interfaces.users import CreateUserData
from src.application.use_cases.auth.authenticate import AuthenticatePrincipalUseCase
from src.application.use_cases.auth.exceptions import InactiveUserError, InvalidAccessTokenError
from src.application.use_cases.auth.permissions import SERVICE_PRINCIPAL_USER_ID
from src.application.utility.secret_tokens import generate_service_key, hash_token
from src.domain.enums import UserRole
from src.infrastructure.auth.access_tokens import JwtAccessTokenCodec
from tests.application.use_cases.auth.fakes import (
    InMemoryServiceApiKeyRepository,
    InMemoryUserRepository,
)

_ACCESS_TOKENS = JwtAccessTokenCodec(secret="test-secret")


def _make_use_case(
    users: InMemoryUserRepository, service_api_keys: InMemoryServiceApiKeyRepository
) -> AuthenticatePrincipalUseCase:
    return AuthenticatePrincipalUseCase(
        users=users, service_api_keys=service_api_keys, access_tokens=_ACCESS_TOKENS
    )


@pytest.mark.asyncio
async def test_authenticate_bearer_returns_the_session_user() -> None:
    users = InMemoryUserRepository()
    use_case = _make_use_case(users, InMemoryServiceApiKeyRepository())
    user = await users.create_user(
        CreateUserData(id="u1", username="alice", password_hash="hash", role=UserRole.USER)
    )
    token = _ACCESS_TOKENS.encode(
        subject=user.id, role=user.role.value, via="session", ttl_seconds=900
    )

    principal = await use_case.authenticate_bearer(token)

    assert principal.via == "session"
    assert principal.user.id == user.id


@pytest.mark.asyncio
async def test_authenticate_bearer_rejects_a_deactivated_user() -> None:
    users = InMemoryUserRepository()
    use_case = _make_use_case(users, InMemoryServiceApiKeyRepository())
    user = await users.create_user(
        CreateUserData(
            id="u1", username="alice", password_hash="hash", role=UserRole.USER, is_active=False
        )
    )
    token = _ACCESS_TOKENS.encode(
        subject=user.id, role=user.role.value, via="session", ttl_seconds=900
    )

    with pytest.raises(InactiveUserError):
        await use_case.authenticate_bearer(token)


@pytest.mark.asyncio
async def test_authenticate_service_key_returns_a_full_admin_principal_not_bound_to_a_user() -> (
    None
):
    service_api_keys = InMemoryServiceApiKeyRepository()
    plaintext = generate_service_key()
    await service_api_keys.replace(
        id="key-1", prefix=plaintext[:12], key_hash=hash_token(plaintext)
    )
    use_case = _make_use_case(InMemoryUserRepository(), service_api_keys)

    principal = await use_case.authenticate_service_key(plaintext)

    assert principal.via == "service"
    assert principal.is_admin
    assert principal.user.id == SERVICE_PRINCIPAL_USER_ID
    assert principal.owner_id is None
    assert service_api_keys.key is not None
    assert service_api_keys.key.last_used_at is not None


@pytest.mark.asyncio
async def test_authenticate_service_key_rejects_an_unknown_key() -> None:
    use_case = _make_use_case(InMemoryUserRepository(), InMemoryServiceApiKeyRepository())

    with pytest.raises(InvalidAccessTokenError):
        await use_case.authenticate_service_key("rlsr_not-a-real-key")
