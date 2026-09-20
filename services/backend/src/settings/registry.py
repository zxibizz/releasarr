"""Registry of runtime-editable settings.

This is the single declaration of which :class:`~src.settings.config.AppSettings`
fields the API exposes and how. Each entry names its field, the UI section it
belongs to, its value shape, whether it carries a secret, and whether a change
needs a process restart to take effect. The registry drives PATCH validation,
the ``locked_keys`` and section payloads of the read response, and the value
coercion in the provider, so the three never disagree about what is editable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, get_args

SettingsSection = Literal[
    "general",
    "services",
    "network",
    "metadata",
    "tasks",
    "logging",
]

ValueKind = Literal["str", "int", "float", "bool", "str_list", "str_optional", "int_optional"]

# Which integration each testable connection belongs to.
IntegrationName = Literal["sonarr", "radarr", "prowlarr", "qbittorrent", "tvdb", "tmdb"]

INTEGRATIONS: tuple[IntegrationName, ...] = (
    "sonarr",
    "radarr",
    "prowlarr",
    "qbittorrent",
    "tvdb",
    "tmdb",
)


@dataclass(frozen=True, slots=True)
class SettingField:
    """One runtime-editable AppSettings field."""

    key: str
    section: SettingsSection
    kind: ValueKind
    is_secret: bool = False
    requires_restart: bool = False
    choices: tuple[str, ...] = ()


# Order matters: it is the order sections and their fields surface in the UI.
SETTING_FIELDS: tuple[SettingField, ...] = (
    # --- general ---
    SettingField("release_missing_grace_seconds", "general", "int"),
    # --- tasks ---
    SettingField("regrab_batch_size", "tasks", "int"),
    SettingField("regrab_indexer_delay_seconds", "tasks", "float"),
    # --- services: Sonarr / Radarr ---
    SettingField("sonarr_url", "services", "str"),
    SettingField("sonarr_api_key", "services", "str", is_secret=True),
    SettingField("sonarr_quality_profile_id", "services", "int_optional"),
    SettingField("radarr_url", "services", "str"),
    SettingField("radarr_api_key", "services", "str", is_secret=True),
    SettingField("radarr_quality_profile_id", "services", "int_optional"),
    # --- services: Prowlarr ---
    SettingField("prowlarr_url", "services", "str"),
    SettingField("prowlarr_api_key", "services", "str", is_secret=True),
    SettingField("prowlarr_categories", "services", "str_list"),
    # --- services: qBittorrent ---
    SettingField("qbittorrent_url", "services", "str"),
    SettingField("qbittorrent_username", "services", "str"),
    SettingField("qbittorrent_password", "services", "str", is_secret=True),
    SettingField("qbittorrent_save_path", "services", "str_optional"),
    SettingField("qbittorrent_category", "services", "str_optional"),
    SettingField("qbittorrent_tag_prefix", "services", "str_optional"),
    SettingField("qbittorrent_paused", "services", "bool"),
    # --- network ---
    SettingField("auth_access_token_ttl_seconds", "network", "int", requires_restart=True),
    SettingField("auth_refresh_token_ttl_seconds", "network", "int", requires_restart=True),
    SettingField("auth_refresh_remember_ttl_seconds", "network", "int", requires_restart=True),
    SettingField("auth_refresh_reuse_grace_seconds", "network", "int", requires_restart=True),
    SettingField("auth_cookie_name", "network", "str", requires_restart=True),
    SettingField("auth_cookie_path", "network", "str", requires_restart=True),
    SettingField("auth_cookie_secure", "network", "bool", requires_restart=True),
    SettingField(
        "auth_cookie_samesite",
        "network",
        "str",
        requires_restart=True,
        choices=("lax", "strict", "none"),
    ),
    SettingField("auth_max_failed_logins", "network", "int"),
    SettingField("auth_lockout_seconds", "network", "int"),
    SettingField("prowlarr_timeout", "network", "float"),
    SettingField("prowlarr_search_timeout", "network", "float"),
    SettingField("prowlarr_search_retries", "network", "int"),
    SettingField("prowlarr_search_concurrency", "network", "int"),
    SettingField("qbittorrent_timeout", "network", "float"),
    SettingField("default_page_size", "network", "int"),
    SettingField("max_page_size", "network", "int"),
    # --- metadata providers ---
    SettingField("tvdb_base_url", "metadata", "str"),
    SettingField("tvdb_api_key", "metadata", "str", is_secret=True),
    SettingField("tmdb_base_url", "metadata", "str"),
    SettingField("tmdb_api_key", "metadata", "str", is_secret=True),
    SettingField("metadata_languages", "metadata", "str_list"),
    # --- logging ---
    SettingField("log_level", "logging", "str", choices=("DEBUG", "INFO", "WARNING", "ERROR")),
    SettingField("log_json", "logging", "bool"),
    SettingField("log_history_files", "logging", "int"),
)

FIELDS_BY_KEY: dict[str, SettingField] = {field.key: field for field in SETTING_FIELDS}

# Fields intentionally NOT editable at runtime. These are read-only in the UI:
# the process identity and storage are fixed by how the container starts, and
# changing them live would orphan in-flight work.
READONLY_KEYS: tuple[str, ...] = (
    "api_title",
    "api_version",
    "api_host",
    "api_port",
    "database_url",
    "auth_secret",
    "log_file",
    "scheduler_log_file",
)

SECTION_KEYS: tuple[SettingsSection, ...] = get_args(SettingsSection)


def coerce_value(field: SettingField, value: Any) -> Any:
    """Coerce a raw JSON value to the field's declared shape, raising on mismatch.

    The settings row stores plain JSON; this is the one place that turns it back
    into a value an ``AppSettings`` field accepts, so validation lives here
    rather than being repeated at every use.
    """

    if field.kind == "str_optional" and value is None:
        return None
    if field.kind == "int_optional" and value is None:
        return None

    if value is None:
        raise ValueError(f"{field.key} must not be null")

    if field.kind == "str":
        if not isinstance(value, str):
            raise ValueError(f"{field.key} must be a string")
    elif field.kind == "str_optional":
        if not isinstance(value, str):
            raise ValueError(f"{field.key} must be a string or null")
    elif field.kind == "int":
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{field.key} must be an integer")
    elif field.kind == "int_optional":
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{field.key} must be an integer or null")
    elif field.kind == "float":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{field.key} must be a number")
        value = float(value)
    elif field.kind == "bool":
        if not isinstance(value, bool):
            raise ValueError(f"{field.key} must be a boolean")
    elif field.kind == "str_list":
        if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
            raise ValueError(f"{field.key} must be a list of strings")

    if field.choices and value not in field.choices:
        raise ValueError(f"{field.key} must be one of {', '.join(field.choices)}")

    return value


__all__ = [
    "FIELDS_BY_KEY",
    "INTEGRATIONS",
    "READONLY_KEYS",
    "SECTION_KEYS",
    "SETTING_FIELDS",
    "IntegrationName",
    "SettingField",
    "SettingsSection",
    "coerce_value",
]
