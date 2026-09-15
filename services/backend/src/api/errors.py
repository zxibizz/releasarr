"""Common error helpers and handlers for the API layer.

Domain exceptions are translated into the canonical error response shape by a
single registry of handlers (see :data:`DOMAIN_ERROR_MAP` and
:func:`register_exception_handlers`), so individual routes no longer need to
wrap use-case calls in repetitive ``try``/``except`` blocks.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping, Sequence
from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from loguru import logger

from src.application.interfaces.indexers import IndexerNotFoundError
from src.application.interfaces.releases import ReleaseSearchUnavailableError
from src.application.use_cases.auth.exceptions import (
    AccountLockedError,
    InactiveUserError,
    InvalidAccessTokenError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    SetupAlreadyCompletedError,
)
from src.application.use_cases.discover.exceptions import (
    DisallowedRootFolderError,
    InvalidRootFolderError,
    MediaNotFoundError,
    MetadataProviderUnavailableError,
    NoQualityProfileError,
    SeasonSelectionError,
    SeasonsUnmanageableError,
)
from src.application.use_cases.indexers.exceptions import ProwlarrNotConfiguredError
from src.application.use_cases.releases.exceptions import (
    ExistingReleasesDecisionRequiredError,
    ReleaseActionNotAllowedError,
    ReleaseConflictError,
    ReleaseDownloadConflictError,
    ReleaseDownloadFailedError,
    ReleaseFileNotFoundError,
    ReleaseNotFoundError,
)
from src.application.use_cases.requests.exceptions import (
    EmptyUpdatePayloadError,
    MediaRequestNotFoundError,
)
from src.application.use_cases.tasks.exceptions import SyncJobNotFoundError
from src.application.use_cases.users.exceptions import (
    LastAdminError,
    UsernameTakenError,
    UserNotFoundError,
)
from src.infrastructure.http import HttpClientError

ErrorDetail = Mapping[str, Any] | Sequence[Any] | None
Handler = Callable[[Request, Exception], Awaitable[JSONResponse]]

# Maps a domain exception type to the (status code, error code) it should emit.
DOMAIN_ERROR_MAP: dict[type[Exception], tuple[int, str]] = {
    MediaRequestNotFoundError: (status.HTTP_404_NOT_FOUND, "request_not_found"),
    EmptyUpdatePayloadError: (status.HTTP_400_BAD_REQUEST, "empty_update"),
    ReleaseNotFoundError: (status.HTTP_404_NOT_FOUND, "release_not_found"),
    ReleaseFileNotFoundError: (status.HTTP_404_NOT_FOUND, "release_file_not_found"),
    ReleaseActionNotAllowedError: (status.HTTP_409_CONFLICT, "release_action_conflict"),
    ReleaseConflictError: (status.HTTP_409_CONFLICT, "release_conflict"),
    ReleaseDownloadConflictError: (status.HTTP_409_CONFLICT, "release_download_conflict"),
    ReleaseDownloadFailedError: (status.HTTP_500_INTERNAL_SERVER_ERROR, "release_download_failed"),
    ReleaseSearchUnavailableError: (status.HTTP_502_BAD_GATEWAY, "upstream_error"),
    ExistingReleasesDecisionRequiredError: (
        status.HTTP_409_CONFLICT,
        "existing_releases_decision_required",
    ),
    SyncJobNotFoundError: (status.HTTP_404_NOT_FOUND, "sync_job_not_found"),
    MetadataProviderUnavailableError: (
        status.HTTP_503_SERVICE_UNAVAILABLE,
        "metadata_provider_unavailable",
    ),
    MediaNotFoundError: (status.HTTP_404_NOT_FOUND, "media_not_found"),
    NoQualityProfileError: (status.HTTP_400_BAD_REQUEST, "no_quality_profile"),
    InvalidRootFolderError: (status.HTTP_400_BAD_REQUEST, "invalid_root_folder"),
    SeasonSelectionError: (status.HTTP_400_BAD_REQUEST, "invalid_season_selection"),
    SeasonsUnmanageableError: (status.HTTP_409_CONFLICT, "seasons_unmanageable"),
    IndexerNotFoundError: (status.HTTP_404_NOT_FOUND, "indexer_not_found"),
    ProwlarrNotConfiguredError: (
        status.HTTP_503_SERVICE_UNAVAILABLE,
        "prowlarr_not_configured",
    ),
    DisallowedRootFolderError: (status.HTTP_403_FORBIDDEN, "root_folder_not_allowed"),
    InvalidCredentialsError: (status.HTTP_401_UNAUTHORIZED, "invalid_credentials"),
    AccountLockedError: (status.HTTP_423_LOCKED, "account_locked"),
    InactiveUserError: (status.HTTP_403_FORBIDDEN, "user_inactive"),
    InvalidRefreshTokenError: (status.HTTP_401_UNAUTHORIZED, "invalid_refresh_token"),
    InvalidAccessTokenError: (status.HTTP_401_UNAUTHORIZED, "invalid_token"),
    SetupAlreadyCompletedError: (status.HTTP_409_CONFLICT, "setup_complete"),
    UserNotFoundError: (status.HTTP_404_NOT_FOUND, "user_not_found"),
    UsernameTakenError: (status.HTTP_409_CONFLICT, "username_taken"),
    LastAdminError: (status.HTTP_409_CONFLICT, "last_admin"),
    # Sonarr, Radarr and the metadata providers all report through this one, so a
    # failure of theirs surfaces as a bad gateway rather than our own crash.
    HttpClientError: (status.HTTP_502_BAD_GATEWAY, "upstream_error"),
}


def _error_payload(code: str, message: str, details: ErrorDetail = None) -> dict[str, Any]:
    return {"code": code, "message": message, "details": details}


def api_error(
    status_code: int,
    code: str,
    message: str,
    details: ErrorDetail = None,
) -> HTTPException:
    """Raiseable HTTP exception producing a spec-compliant error body."""

    payload = _error_payload(code, message, details)
    return HTTPException(status_code=status_code, detail=payload)


def _domain_handler(status_code: int, code: str) -> Handler:
    async def handler(request: Request, exc: Exception) -> JSONResponse:
        details = getattr(exc, "details", None)
        payload = _error_payload(code, str(exc), details)
        return JSONResponse(status_code=status_code, content=payload)

    return handler


async def validation_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Translate FastAPI validation errors into the standardized response body."""

    errors = exc.errors() if isinstance(exc, RequestValidationError) else []
    detail = _error_payload("validation_error", "Request validation failed", errors)
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, content=detail)


async def http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Ensure HTTP exceptions emit the canonical error response shape."""

    status_code = exc.status_code if isinstance(exc, HTTPException) else 500
    detail = exc.detail if isinstance(exc, HTTPException) else None
    if isinstance(detail, dict) and {"code", "message"}.issubset(detail.keys()):
        payload = _error_payload(detail["code"], detail["message"], detail.get("details"))
    else:
        message = detail if isinstance(detail, str) else str(detail or status_code)
        payload = _error_payload("http_error", message)
    return JSONResponse(status_code=status_code, content=payload)


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Fallback handler for unexpected errors."""

    # The response deliberately says nothing about the cause, so this is the only
    # record that the crash ever happened.
    logger.opt(exception=exc).error(
        f"Unhandled error serving {request.method} {request.url.path}",
        method=request.method,
        path=request.url.path,
        error=str(exc),
    )
    payload = _error_payload("internal_error", "An unexpected error occurred")
    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=payload)


def register_exception_handlers(app: FastAPI) -> None:
    """Register validation, domain, and fallback exception handlers on ``app``."""

    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    for exc_type, (status_code, code) in DOMAIN_ERROR_MAP.items():
        app.add_exception_handler(exc_type, _domain_handler(status_code, code))
    app.add_exception_handler(Exception, unhandled_exception_handler)


__all__ = [
    "DOMAIN_ERROR_MAP",
    "api_error",
    "http_exception_handler",
    "register_exception_handlers",
    "unhandled_exception_handler",
    "validation_exception_handler",
]
