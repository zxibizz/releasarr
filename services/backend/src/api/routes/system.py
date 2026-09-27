"""FastAPI routes describing the running instance."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from src.api.dependencies import require_user
from src.api.responses import AUTH_REQUIRED_RESPONSES, error_responses
from src.application.use_cases.system import GetSystemInfoUseCase
from src.core.container import AppContainer, get_container
from src.schemas.system import SystemInfo

router = APIRouter(prefix="/system", tags=["System"], dependencies=[Depends(require_user)])


def _get_container() -> AppContainer:
    return get_container()


def _get_use_case(container: AppContainer = Depends(_get_container)) -> GetSystemInfoUseCase:
    return container.use_cases.system.info


@router.get(
    "/status", response_model=SystemInfo, responses=error_responses(AUTH_REQUIRED_RESPONSES)
)
async def get_system_status(
    use_case: GetSystemInfoUseCase = Depends(_get_use_case),
) -> SystemInfo:
    info = await use_case.execute()
    return SystemInfo.model_validate(info)


__all__ = ["router"]
