"""The single, always-present service API key: admin access, no user binding."""

from __future__ import annotations

from uuid import uuid4

from src.application.interfaces.auth import ServiceApiKeyRecord, ServiceApiKeyRepository
from src.application.utility.secret_tokens import generate_service_key
from src.core.logging import get_logger
from src.domain.enums import LogComponent

_logger = get_logger(LogComponent.USECASE_AUTH)


class GetOrCreateServiceApiKeyUseCase:
    """Return the service key, generating it on first use, as Sonarr does at first launch."""

    def __init__(self, *, service_api_keys: ServiceApiKeyRepository) -> None:
        self._service_api_keys = service_api_keys

    async def execute(self) -> ServiceApiKeyRecord:
        existing = await self._service_api_keys.get()
        if existing is not None:
            return existing
        return await self._service_api_keys.replace(id=uuid4().hex, key=generate_service_key())


class RegenerateServiceApiKeyUseCase:
    """Rotate the service key, invalidating the old one."""

    def __init__(self, *, service_api_keys: ServiceApiKeyRepository) -> None:
        self._service_api_keys = service_api_keys

    async def execute(self) -> ServiceApiKeyRecord:
        _logger.info("Service API key regenerated")
        return await self._service_api_keys.replace(id=uuid4().hex, key=generate_service_key())


__all__ = ["GetOrCreateServiceApiKeyUseCase", "RegenerateServiceApiKeyUseCase"]
