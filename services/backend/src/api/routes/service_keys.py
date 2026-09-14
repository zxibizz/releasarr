"""FastAPI routes for admin-managed service API keys."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Path, status

from src.api.dependencies import require_admin
from src.api.responses import ADMIN_REQUIRED_RESPONSES, error_responses
from src.application.use_cases.users import (
    CreateServiceKeyCommand,
    CreateServiceKeyUseCase,
    ListServiceKeysUseCase,
    RevokeServiceKeyUseCase,
)
from src.core.container import AppContainer, get_container
from src.schemas.users import (
    CreateServiceKeyPayload,
    ServiceApiKey,
    ServiceApiKeyCreated,
    ServiceApiKeysResponse,
)

router = APIRouter(prefix="/service-keys", tags=["Users"], dependencies=[Depends(require_admin)])

_SERVER_ERROR = "Unexpected server error."

CREATE_KEY_RESPONSES = error_responses(
    {
        **ADMIN_REQUIRED_RESPONSES,
        status.HTTP_404_NOT_FOUND: "The user this key would act as does not exist.",
        status.HTTP_500_INTERNAL_SERVER_ERROR: _SERVER_ERROR,
    }
)

KEY_NOT_FOUND_RESPONSES = error_responses(
    {
        **ADMIN_REQUIRED_RESPONSES,
        status.HTTP_404_NOT_FOUND: "Service key not found.",
        status.HTTP_500_INTERNAL_SERVER_ERROR: _SERVER_ERROR,
    }
)

LIST_KEYS_RESPONSES = error_responses({**ADMIN_REQUIRED_RESPONSES})


def _get_container() -> AppContainer:
    return get_container()


def _create_use_case(container: AppContainer = Depends(_get_container)) -> CreateServiceKeyUseCase:
    return container.use_cases.users.create_service_key


def _list_use_case(container: AppContainer = Depends(_get_container)) -> ListServiceKeysUseCase:
    return container.use_cases.users.list_service_keys


def _revoke_use_case(container: AppContainer = Depends(_get_container)) -> RevokeServiceKeyUseCase:
    return container.use_cases.users.revoke_service_key


KeyIdParam = Annotated[str, Path(..., alias="keyId")]


@router.get("", response_model=ServiceApiKeysResponse, responses=LIST_KEYS_RESPONSES)
async def list_service_keys(
    use_case: ListServiceKeysUseCase = Depends(_list_use_case),
) -> ServiceApiKeysResponse:
    keys = await use_case.execute()
    return ServiceApiKeysResponse(service_keys=[ServiceApiKey.model_validate(key) for key in keys])


@router.post(
    "",
    response_model=ServiceApiKeyCreated,
    status_code=status.HTTP_201_CREATED,
    responses=CREATE_KEY_RESPONSES,
)
async def create_service_key(
    payload: CreateServiceKeyPayload,
    use_case: CreateServiceKeyUseCase = Depends(_create_use_case),
) -> ServiceApiKeyCreated:
    record, plaintext = await use_case.execute(
        CreateServiceKeyCommand(
            name=payload.name,
            user_id=payload.user_id,
            can_impersonate=payload.can_impersonate,
            expires_at=payload.expires_at,
        )
    )
    return ServiceApiKeyCreated(key=ServiceApiKey.model_validate(record), plaintext=plaintext)


@router.delete(
    "/{keyId}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=KEY_NOT_FOUND_RESPONSES,
)
async def revoke_service_key(
    key_id: KeyIdParam, use_case: RevokeServiceKeyUseCase = Depends(_revoke_use_case)
) -> None:
    await use_case.execute(key_id)


__all__ = ["router"]
