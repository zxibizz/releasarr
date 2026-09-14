"""Auth use case exports."""

from src.application.use_cases.auth.authenticate import AuthenticatePrincipalUseCase
from src.application.use_cases.auth.bootstrap_admin import BootstrapAdminUseCase
from src.application.use_cases.auth.commands import BootstrapAdminCommand, LoginCommand
from src.application.use_cases.auth.dto import IssuedSessionDTO
from src.application.use_cases.auth.exceptions import (
    AccountLockedError,
    InactiveUserError,
    InvalidAccessTokenError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    PermissionDeniedError,
    SetupAlreadyCompletedError,
)
from src.application.use_cases.auth.login import LoginUseCase
from src.application.use_cases.auth.logout import LogoutUseCase
from src.application.use_cases.auth.permissions import (
    Permission,
    Principal,
    RequestScope,
    allowed_root_folders,
    has_permission,
)
from src.application.use_cases.auth.refresh_session import RefreshSessionUseCase
from src.application.use_cases.auth.service_key import (
    GetOrCreateServiceApiKeyUseCase,
    RegenerateServiceApiKeyUseCase,
)
from src.application.use_cases.auth.session_issuer import SessionIssuer
from src.application.use_cases.auth.setup_status import GetSetupStatusUseCase

__all__ = [
    "AccountLockedError",
    "AuthenticatePrincipalUseCase",
    "BootstrapAdminCommand",
    "BootstrapAdminUseCase",
    "GetOrCreateServiceApiKeyUseCase",
    "GetSetupStatusUseCase",
    "InactiveUserError",
    "InvalidAccessTokenError",
    "InvalidCredentialsError",
    "InvalidRefreshTokenError",
    "IssuedSessionDTO",
    "LoginCommand",
    "LoginUseCase",
    "LogoutUseCase",
    "Permission",
    "PermissionDeniedError",
    "Principal",
    "RefreshSessionUseCase",
    "RegenerateServiceApiKeyUseCase",
    "RequestScope",
    "SessionIssuer",
    "SetupAlreadyCompletedError",
    "allowed_root_folders",
    "has_permission",
]

