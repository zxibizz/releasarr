"""FastAPI routes for the singleton service API key (admin access, Sonarr-style)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from src.api.dependencies import require_admin
from src.api.responses import ADMIN_REQUIRED_RESPONSES, error_responses
from src.application.use_cases.auth import (
    GetOrCreateServiceApiKeyUseCase,
    RegenerateServiceApiKeyUseCase,
)
from src.core.container import AppContainer, get_container
from src.schemas.auth import ServiceApiKeyCreated, ServiceApiKeyInfo

router = APIRouter(prefix="/service-key", tags=["Auth"], dependencies=[Depends(require_admin)])

KEY_RESPONSES = error_responses({**ADMIN_REQUIRED_RESPONSES})


def _get_container() -> AppContainer:
    return get_container()


def _get_use_case(
    container: AppContainer = Depends(_get_container),
) -> GetOrCreateServiceApiKeyUseCase:
    return container.use_cases.auth.service_key


def _regenerate_use_case(
    container: AppContainer = Depends(_get_container),
) -> RegenerateServiceApiKeyUseCase:
    return container.use_cases.auth.regenerate_service_key


@router.get("", response_model=ServiceApiKeyInfo, responses=KEY_RESPONSES)
async def get_service_key(
    use_case: GetOrCreateServiceApiKeyUseCase = Depends(_get_use_case),
) -> ServiceApiKeyInfo:
    record = await use_case.execute()
    return ServiceApiKeyInfo.model_validate(record)


@router.post("/regenerate", response_model=ServiceApiKeyCreated, responses=KEY_RESPONSES)
async def regenerate_service_key(
    use_case: RegenerateServiceApiKeyUseCase = Depends(_regenerate_use_case),
) -> ServiceApiKeyCreated:
    record, plaintext = await use_case.execute()
    return ServiceApiKeyCreated(key=ServiceApiKeyInfo.model_validate(record), plaintext=plaintext)


__all__ = ["router"]

