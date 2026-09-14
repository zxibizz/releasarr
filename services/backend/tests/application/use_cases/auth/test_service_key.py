"""Tests for the singleton service API key use cases."""

from __future__ import annotations

import pytest

from src.application.use_cases.auth.service_key import (
    GetOrCreateServiceApiKeyUseCase,
    RegenerateServiceApiKeyUseCase,
)
from src.application.utility.secret_tokens import SERVICE_KEY_PREFIX
from tests.application.use_cases.auth.fakes import InMemoryServiceApiKeyRepository


@pytest.mark.asyncio
async def test_get_or_create_generates_a_key_on_first_use() -> None:
    repo = InMemoryServiceApiKeyRepository()
    use_case = GetOrCreateServiceApiKeyUseCase(service_api_keys=repo)

    record = await use_case.execute()

    assert record.key.startswith(SERVICE_KEY_PREFIX)
    assert repo.key is record


@pytest.mark.asyncio
async def test_get_or_create_returns_the_existing_key_on_later_calls() -> None:
    repo = InMemoryServiceApiKeyRepository()
    use_case = GetOrCreateServiceApiKeyUseCase(service_api_keys=repo)

    first = await use_case.execute()
    second = await use_case.execute()

    assert second.id == first.id
    assert second.key == first.key


@pytest.mark.asyncio
async def test_regenerate_replaces_the_key_and_invalidates_the_old_one() -> None:
    repo = InMemoryServiceApiKeyRepository()
    use_case = GetOrCreateServiceApiKeyUseCase(service_api_keys=repo)
    regenerate = RegenerateServiceApiKeyUseCase(service_api_keys=repo)

    original = await use_case.execute()
    new_record = await regenerate.execute()

    assert new_record.id != original.id
    assert new_record.key != original.key
    assert await repo.get_by_key(original.key) is None
    assert await repo.get_by_key(new_record.key) == new_record
