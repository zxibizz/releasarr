"""Runtime settings use cases."""

from src.application.use_cases.settings.exceptions import (
    EmptySettingsUpdateError,
    InvalidSettingValueError,
    SettingLockedError,
    SettingsError,
    UnknownSettingKeyError,
)
from src.application.use_cases.settings.get_settings import GetSettingsUseCase, SettingsView
from src.application.use_cases.settings.list_options import (
    IndexerCategoryOptionDTO,
    ListDownloadCategoriesUseCase,
    ListIndexerCategoriesUseCase,
    ListQualityProfilesUseCase,
    QualityProfileOptionDTO,
)
from src.application.use_cases.settings.test_connection import (
    ConnectionTestCommand,
    ConnectionTestResultDTO,
    TestIntegrationConnectionUseCase,
)
from src.application.use_cases.settings.update_section import UpdateSettingsSectionUseCase

__all__ = [
    "ConnectionTestCommand",
    "ConnectionTestResultDTO",
    "EmptySettingsUpdateError",
    "GetSettingsUseCase",
    "IndexerCategoryOptionDTO",
    "InvalidSettingValueError",
    "ListDownloadCategoriesUseCase",
    "ListIndexerCategoriesUseCase",
    "ListQualityProfilesUseCase",
    "QualityProfileOptionDTO",
    "SettingLockedError",
    "SettingsError",
    "SettingsView",
    "TestIntegrationConnectionUseCase",
    "UnknownSettingKeyError",
    "UpdateSettingsSectionUseCase",
]
