"""FastAPI routes for admin-managed user accounts."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Path, status

from src.api.dependencies import require_admin, require_user
from src.api.responses import ADMIN_REQUIRED_RESPONSES, AUTH_REQUIRED_RESPONSES, error_responses
from src.application.use_cases.auth import Principal
from src.application.use_cases.users import (
    ChangePasswordCommand,
    ChangePasswordUseCase,
    CreateUserCommand,
    CreateUserUseCase,
    DeleteUserUseCase,
    GetUserUseCase,
    ListUsersUseCase,
    UpdateUserCommand,
    UpdateUserUseCase,
)
from src.application.utility.sentinels import UNSET
from src.core.container import AppContainer, get_container
from src.domain.enums import UserRole
from src.schemas.users import (
    ChangePasswordPayload,
    CreateUserPayload,
    UpdateUserPayload,
    User,
    UsersResponse,
)

router = APIRouter(prefix="/users", tags=["Users"])

_SERVER_ERROR = "Unexpected server error."

USER_NOT_FOUND_RESPONSES = error_responses(
    {
        **ADMIN_REQUIRED_RESPONSES,
        status.HTTP_404_NOT_FOUND: "User not found.",
        status.HTTP_500_INTERNAL_SERVER_ERROR: _SERVER_ERROR,
    }
)

CREATE_USER_RESPONSES = error_responses(
    {
        **ADMIN_REQUIRED_RESPONSES,
        status.HTTP_409_CONFLICT: "Username is already taken.",
        status.HTTP_422_UNPROCESSABLE_CONTENT: "Validation failed for the provided fields.",
        status.HTTP_500_INTERNAL_SERVER_ERROR: _SERVER_ERROR,
    }
)

UPDATE_USER_RESPONSES = error_responses(
    {
        **ADMIN_REQUIRED_RESPONSES,
        status.HTTP_404_NOT_FOUND: "User not found.",
        status.HTTP_409_CONFLICT: "This change would remove the last active admin.",
        status.HTTP_500_INTERNAL_SERVER_ERROR: _SERVER_ERROR,
    }
)

LIST_USERS_RESPONSES = error_responses({**ADMIN_REQUIRED_RESPONSES})
CHANGE_PASSWORD_RESPONSES = error_responses({**AUTH_REQUIRED_RESPONSES})


def _get_container() -> AppContainer:
    return get_container()


def _list_use_case(container: AppContainer = Depends(_get_container)) -> ListUsersUseCase:
    return container.use_cases.users.list


def _get_use_case(container: AppContainer = Depends(_get_container)) -> GetUserUseCase:
    return container.use_cases.users.get


def _create_use_case(container: AppContainer = Depends(_get_container)) -> CreateUserUseCase:
    return container.use_cases.users.create


def _update_use_case(container: AppContainer = Depends(_get_container)) -> UpdateUserUseCase:
    return container.use_cases.users.update


def _delete_use_case(container: AppContainer = Depends(_get_container)) -> DeleteUserUseCase:
    return container.use_cases.users.delete


def _change_password_use_case(
    container: AppContainer = Depends(_get_container),
) -> ChangePasswordUseCase:
    return container.use_cases.users.change_password


UserIdParam = Annotated[str, Path(..., alias="userId")]


@router.get(
    "",
    response_model=UsersResponse,
    responses=LIST_USERS_RESPONSES,
    dependencies=[Depends(require_admin)],
)
async def list_users(use_case: ListUsersUseCase = Depends(_list_use_case)) -> UsersResponse:
    users = await use_case.execute()
    return UsersResponse(users=[User.model_validate(user) for user in users])


@router.post(
    "",
    response_model=User,
    status_code=status.HTTP_201_CREATED,
    responses=CREATE_USER_RESPONSES,
    dependencies=[Depends(require_admin)],
)
async def create_user(
    payload: CreateUserPayload,
    use_case: CreateUserUseCase = Depends(_create_use_case),
) -> User:
    user = await use_case.execute(
        CreateUserCommand(
            username=payload.username,
            password=payload.password,
            role=UserRole(payload.role),
            display_name=payload.display_name,
            is_active=payload.is_active,
            can_view_all_requests=payload.can_view_all_requests,
            can_access_tasks=payload.can_access_tasks,
            can_access_indexers=payload.can_access_indexers,
            can_access_logs=payload.can_access_logs,
            allowed_root_folders=list(payload.allowed_root_folders),
        )
    )
    return User.model_validate(user)


@router.get(
    "/{userId}",
    response_model=User,
    responses=USER_NOT_FOUND_RESPONSES,
    dependencies=[Depends(require_admin)],
)
async def get_user(user_id: UserIdParam, use_case: GetUserUseCase = Depends(_get_use_case)) -> User:
    user = await use_case.execute(user_id)
    return User.model_validate(user)


@router.patch(
    "/{userId}",
    response_model=User,
    responses=UPDATE_USER_RESPONSES,
    dependencies=[Depends(require_admin)],
)
async def update_user(
    user_id: UserIdParam,
    payload: UpdateUserPayload,
    use_case: UpdateUserUseCase = Depends(_update_use_case),
) -> User:
    command = UpdateUserCommand()
    for field_name in payload.model_fields_set:
        value = getattr(payload, field_name)
        if field_name == "role" and value is not None:
            value = UserRole(value)
        if field_name == "password":
            setattr(command, "password", value if value is not None else UNSET)
            continue
        setattr(command, field_name, value)
    user = await use_case.execute(user_id, command)
    return User.model_validate(user)


@router.delete(
    "/{userId}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=UPDATE_USER_RESPONSES,
    dependencies=[Depends(require_admin)],
)
async def delete_user(
    user_id: UserIdParam, use_case: DeleteUserUseCase = Depends(_delete_use_case)
) -> None:
    await use_case.execute(user_id)


@router.post(
    "/me/password", status_code=status.HTTP_204_NO_CONTENT, responses=CHANGE_PASSWORD_RESPONSES
)
async def change_own_password(
    payload: ChangePasswordPayload,
    principal: Principal = Depends(require_user),
    use_case: ChangePasswordUseCase = Depends(_change_password_use_case),
) -> None:
    await use_case.execute(
        principal.user.id,
        ChangePasswordCommand(
            current_password=payload.current_password,
            new_password=payload.new_password,
        ),
    )


__all__ = ["router"]
