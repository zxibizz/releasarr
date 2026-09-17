"""FastAPI routes for runtime-editable application settings (admin only)."""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Path, status

from src.api.dependencies import require_admin
from src.api.responses import ADMIN_REQUIRED_RESPONSES, error_responses
from src.application.use_cases.settings import (
    ConnectionTestCommand,
    GetSettingsUseCase,
    ListDownloadCategoriesUseCase,
    ListIndexerCategoriesUseCase,
    ListQualityProfilesUseCase,
    TestIntegrationConnectionUseCase,
    UpdateSettingsSectionUseCase,
)
from src.core.container import AppContainer, get_container
from src.schemas.settings import (
    ConnectionTestPayload,
    ConnectionTestResult,
    DownloadCategoriesResponse,
    IndexerCategoriesResponse,
    IndexerCategoryOption,
    QualityProfileOption,
    QualityProfilesResponse,
    SettingFieldInfo,
    SettingsResponse,
    UpdateSettingsPayload,
)
from src.settings.registry import SETTING_FIELDS, IntegrationName, SettingsSection

router = APIRouter(prefix="/settings", tags=["Settings"], dependencies=[Depends(require_admin)])

SETTINGS_RESPONSES = error_responses(
    {
        **ADMIN_REQUIRED_RESPONSES,
        status.HTTP_500_INTERNAL_SERVER_ERROR: "Unexpected server error.",
    }
)

UPDATE_SETTINGS_RESPONSES = error_responses(
    {
        **ADMIN_REQUIRED_RESPONSES,
        status.HTTP_400_BAD_REQUEST: "No fields supplied, or a value failed validation.",
        status.HTTP_409_CONFLICT: "A field is set by the environment and cannot be changed here.",
        status.HTTP_422_UNPROCESSABLE_CONTENT: "An unknown setting key was supplied.",
        status.HTTP_500_INTERNAL_SERVER_ERROR: "Unexpected server error.",
    }
)

OPTIONS_RESPONSES = error_responses(
    {
        **ADMIN_REQUIRED_RESPONSES,
        status.HTTP_500_INTERNAL_SERVER_ERROR: "Unexpected server error.",
        status.HTTP_502_BAD_GATEWAY: "The service refused or could not answer the lookup.",
        status.HTTP_503_SERVICE_UNAVAILABLE: "The service is not configured yet.",
    }
)


def _get_container() -> AppContainer:
    return get_container()


def _get_use_case(container: AppContainer = Depends(_get_container)) -> GetSettingsUseCase:
    return container.use_cases.settings.get


def _update_use_case(
    container: AppContainer = Depends(_get_container),
) -> UpdateSettingsSectionUseCase:
    return container.use_cases.settings.update_section


def _test_use_case(
    container: AppContainer = Depends(_get_container),
) -> TestIntegrationConnectionUseCase:
    return container.use_cases.settings.test_connection


def _quality_profiles_use_case(
    container: AppContainer = Depends(_get_container),
) -> ListQualityProfilesUseCase:
    return container.use_cases.settings.list_quality_profiles


def _indexer_categories_use_case(
    container: AppContainer = Depends(_get_container),
) -> ListIndexerCategoriesUseCase:
    return container.use_cases.settings.list_indexer_categories


def _download_categories_use_case(
    container: AppContainer = Depends(_get_container),
) -> ListDownloadCategoriesUseCase:
    return container.use_cases.settings.list_download_categories


SectionParam = Annotated[SettingsSection, Path(...)]
IntegrationParam = Annotated[IntegrationName, Path(...)]


def _to_response(view) -> SettingsResponse:
    locked = set(view.locked_keys)
    return SettingsResponse(
        values=view.values,
        fields=[
            SettingFieldInfo(
                key=field.key,
                section=field.section,
                kind=field.kind,
                is_secret=field.is_secret,
                requires_restart=field.requires_restart,
                locked=field.key in locked,
                choices=list(field.choices),
            )
            for field in SETTING_FIELDS
        ],
        locked_keys=view.locked_keys,
        pending_restart_keys=[],
    )


@router.get("", response_model=SettingsResponse, responses=SETTINGS_RESPONSES)
async def get_settings(
    use_case: GetSettingsUseCase = Depends(_get_use_case),
) -> SettingsResponse:
    view = await use_case.execute()
    return _to_response(view)


@router.patch(
    "/{section}",
    response_model=SettingsResponse,
    responses=UPDATE_SETTINGS_RESPONSES,
)
async def update_settings_section(
    section: SectionParam,
    payload: UpdateSettingsPayload,
    update_use_case: UpdateSettingsSectionUseCase = Depends(_update_use_case),
    get_use_case: GetSettingsUseCase = Depends(_get_use_case),
) -> SettingsResponse:
    await update_use_case.execute(section, payload.values)
    view = await get_use_case.execute()
    return _to_response(view)


@router.post(
    "/test/{integration}",
    response_model=ConnectionTestResult,
    responses=SETTINGS_RESPONSES,
)
async def test_integration_connection(
    integration: IntegrationParam,
    payload: ConnectionTestPayload | None = None,
    use_case: TestIntegrationConnectionUseCase = Depends(_test_use_case),
) -> ConnectionTestResult:
    command = (
        ConnectionTestCommand(
            url=payload.url,
            api_key=payload.api_key,
            username=payload.username,
            password=payload.password,
        )
        if payload is not None
        else ConnectionTestCommand()
    )
    result = await use_case.execute(integration, command)
    return ConnectionTestResult(
        integration=result.integration, success=result.success, detail=result.detail
    )


@router.get(
    "/options/quality-profiles/{integration}",
    response_model=QualityProfilesResponse,
    responses=OPTIONS_RESPONSES,
)
async def list_quality_profiles(
    integration: Annotated[Literal["sonarr", "radarr"], Path(...)],
    use_case: ListQualityProfilesUseCase = Depends(_quality_profiles_use_case),
) -> QualityProfilesResponse:
    profiles = await use_case.execute(integration)
    return QualityProfilesResponse(
        profiles=[
            QualityProfileOption(id=profile.profile_id, name=profile.name) for profile in profiles
        ]
    )


@router.get(
    "/options/indexer-categories",
    response_model=IndexerCategoriesResponse,
    responses=OPTIONS_RESPONSES,
)
async def list_indexer_categories(
    use_case: ListIndexerCategoriesUseCase = Depends(_indexer_categories_use_case),
) -> IndexerCategoriesResponse:
    categories = await use_case.execute()
    return IndexerCategoriesResponse(
        categories=[
            IndexerCategoryOption(id=category.category_id, name=category.name)
            for category in categories
        ]
    )


@router.get(
    "/options/download-categories",
    response_model=DownloadCategoriesResponse,
    responses=OPTIONS_RESPONSES,
)
async def list_download_categories(
    use_case: ListDownloadCategoriesUseCase = Depends(_download_categories_use_case),
) -> DownloadCategoriesResponse:
    return DownloadCategoriesResponse(categories=await use_case.execute())


__all__ = ["router"]
