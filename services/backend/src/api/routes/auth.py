"""FastAPI routes for authentication: setup, login, refresh, logout, and "me"."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request, Response, status

from src.api.dependencies import require_user
from src.api.errors import api_error
from src.api.responses import AUTH_REQUIRED_RESPONSES, error_responses
from src.application.use_cases.auth import (
    BootstrapAdminCommand,
    BootstrapAdminUseCase,
    GetSetupStatusUseCase,
    IssuedSessionDTO,
    LoginCommand,
    LoginUseCase,
    LogoutUseCase,
    Principal,
    RefreshSessionUseCase,
)
from src.core.container import AppContainer, get_container
from src.schemas.auth import LoginPayload, LoginResponse, SetupPayload, SetupStatus
from src.schemas.users import SessionUser

router = APIRouter(prefix="/auth", tags=["Auth"])

_SERVER_ERROR = "Unexpected server error."

LOGIN_RESPONSES = error_responses(
    {
        status.HTTP_401_UNAUTHORIZED: "Invalid username or password.",
        status.HTTP_423_LOCKED: "Account is temporarily locked.",
        status.HTTP_500_INTERNAL_SERVER_ERROR: _SERVER_ERROR,
    }
)

REFRESH_RESPONSES = error_responses(
    {
        status.HTTP_401_UNAUTHORIZED: "Refresh cookie is missing, invalid, or expired.",
        status.HTTP_500_INTERNAL_SERVER_ERROR: _SERVER_ERROR,
    }
)

SETUP_RESPONSES = error_responses(
    {
        status.HTTP_409_CONFLICT: "Setup has already been completed.",
        status.HTTP_500_INTERNAL_SERVER_ERROR: _SERVER_ERROR,
    }
)


def _get_container() -> AppContainer:
    return get_container()


def _set_refresh_cookie(
    response: Response, container: AppContainer, session: IssuedSessionDTO
) -> None:
    settings = container.settings
    max_age = max(int((session.refresh_expires_at - datetime.now(UTC)).total_seconds()), 0)
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=session.refresh_token,
        max_age=max_age,
        path=settings.auth_cookie_path,
        secure=settings.auth_cookie_secure,
        httponly=True,
        samesite=settings.auth_cookie_samesite,
    )


def _clear_refresh_cookie(response: Response, container: AppContainer) -> None:
    settings = container.settings
    response.delete_cookie(key=settings.auth_cookie_name, path=settings.auth_cookie_path)


def _session_to_response(session: IssuedSessionDTO) -> LoginResponse:
    return LoginResponse(
        access_token=session.access_token, user=SessionUser.model_validate(session.user)
    )


@router.get("/setup", response_model=SetupStatus)
async def get_setup_status(container: AppContainer = Depends(_get_container)) -> SetupStatus:
    use_case: GetSetupStatusUseCase = container.use_cases.auth.setup_status
    return SetupStatus(required=await use_case.execute())


@router.post(
    "/setup",
    response_model=LoginResponse,
    status_code=status.HTTP_201_CREATED,
    responses=SETUP_RESPONSES,
)
async def complete_setup(
    payload: SetupPayload,
    response: Response,
    container: AppContainer = Depends(_get_container),
) -> LoginResponse:
    use_case: BootstrapAdminUseCase = container.use_cases.auth.bootstrap_admin
    session = await use_case.execute(
        BootstrapAdminCommand(
            username=payload.username,
            password=payload.password,
            display_name=payload.display_name,
        )
    )
    _set_refresh_cookie(response, container, session)
    return _session_to_response(session)


@router.post("/login", response_model=LoginResponse, responses=LOGIN_RESPONSES)
async def login(
    payload: LoginPayload,
    response: Response,
    container: AppContainer = Depends(_get_container),
) -> LoginResponse:
    use_case: LoginUseCase = container.use_cases.auth.login
    session = await use_case.execute(
        LoginCommand(
            username=payload.username,
            password=payload.password,
            remember_me=payload.remember_me,
        )
    )
    _set_refresh_cookie(response, container, session)
    return _session_to_response(session)


@router.post("/refresh", response_model=LoginResponse, responses=REFRESH_RESPONSES)
async def refresh(
    request: Request,
    response: Response,
    container: AppContainer = Depends(_get_container),
) -> LoginResponse:
    token = request.cookies.get(container.settings.auth_cookie_name)
    if not token:
        raise api_error(
            status.HTTP_401_UNAUTHORIZED,
            "invalid_refresh_token",
            "No refresh cookie was presented",
        )
    use_case: RefreshSessionUseCase = container.use_cases.auth.refresh
    session = await use_case.execute(token)
    _set_refresh_cookie(response, container, session)
    return _session_to_response(session)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    container: AppContainer = Depends(_get_container),
) -> Response:
    token = request.cookies.get(container.settings.auth_cookie_name)
    use_case: LogoutUseCase = container.use_cases.auth.logout
    await use_case.execute(token)
    _clear_refresh_cookie(response, container)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=SessionUser, responses=error_responses(AUTH_REQUIRED_RESPONSES))
async def get_me(principal: Principal = Depends(require_user)) -> SessionUser:
    return SessionUser.model_validate(principal.user)


__all__ = ["router"]
