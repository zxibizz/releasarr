"""Test an integration's connection, against saved or candidate credentials."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.core.logging import get_logger
from src.domain.enums import LogComponent
from src.settings.config import AppSettings
from src.settings.registry import IntegrationName

logger = get_logger(LogComponent.INTEGRATION_SONARR)


@dataclass(slots=True)
class ConnectionTestResultDTO:
    integration: str
    success: bool
    detail: str | None = None


@dataclass(slots=True)
class ConnectionTestCommand:
    """Candidate credentials; unset fields fall back to the saved configuration."""

    url: str | None = None
    api_key: str | None = None
    username: str | None = None
    password: str | None = None


# Builds a throwaway client for a candidate connection, or returns the saved one
# (second tuple element False) so the live client is not closed underneath the
# container. Candidate clients are closed by the use case after the probe.
def _build_client(
    integration: IntegrationName,
    settings: AppSettings,
    command: ConnectionTestCommand,
) -> tuple[Any, bool]:
    from src.infrastructure.prowlarr import ProwlarrIndexerDirectory
    from src.infrastructure.qbittorrent import QbittorrentClient
    from src.infrastructure.radarr import RadarrHttpClient
    from src.infrastructure.sonarr import SonarrHttpClient
    from src.infrastructure.tmdb import TmdbHttpClient
    from src.infrastructure.tvdb import TvdbHttpClient

    def pick(candidate: str | None, saved: str) -> str:
        return candidate if candidate else saved

    if integration == "sonarr":
        return SonarrHttpClient(
            base_url=pick(command.url, settings.sonarr_url),
            api_key=pick(command.api_key, settings.sonarr_api_key.get_secret_value()),
        ), True
    if integration == "radarr":
        return RadarrHttpClient(
            base_url=pick(command.url, settings.radarr_url),
            api_key=pick(command.api_key, settings.radarr_api_key.get_secret_value()),
        ), True
    if integration == "prowlarr":
        return ProwlarrIndexerDirectory(
            base_url=pick(command.url, settings.prowlarr_url),
            api_key=pick(command.api_key, settings.prowlarr_api_key.get_secret_value()),
        ), True
    if integration == "qbittorrent":
        return QbittorrentClient(
            base_url=pick(command.url, settings.qbittorrent_url),
            username=pick(command.username, settings.qbittorrent_username),
            password=pick(command.password, settings.qbittorrent_password.get_secret_value()),
        ), True
    if integration == "tvdb":
        return TvdbHttpClient(
            base_url=pick(command.url, settings.tvdb_base_url),
            api_token=pick(command.api_key, settings.tvdb_api_key.get_secret_value()),
        ), True
    if integration == "tmdb":
        return TmdbHttpClient(
            base_url=pick(command.url, settings.tmdb_base_url),
            api_token=pick(command.api_key, settings.tmdb_api_key.get_secret_value()),
        ), True
    raise ValueError(f"unknown integration: {integration}")


class TestIntegrationConnectionUseCase:
    def __init__(self, settings: AppSettings) -> None:
        self._settings = settings

    async def execute(
        self,
        integration: IntegrationName,
        command: ConnectionTestCommand | None = None,
    ) -> ConnectionTestResultDTO:
        command = command or ConnectionTestCommand()
        client, is_throwaway = _build_client(integration, self._settings, command)
        try:
            await client.test_connection()
        except Exception as exc:  # httpx errors, auth failures, our own wrappers
            detail = str(exc) or exc.__class__.__name__
            logger.info("Connection test failed", integration=integration, detail=detail)
            return ConnectionTestResultDTO(integration=integration, success=False, detail=detail)
        finally:
            if is_throwaway:
                close = getattr(client, "aclose", None) or getattr(client, "close", None)
                if close is not None:
                    await close()

        logger.info("Connection test succeeded", integration=integration)
        return ConnectionTestResultDTO(integration=integration, success=True)


__all__ = [
    "ConnectionTestCommand",
    "ConnectionTestResultDTO",
    "TestIntegrationConnectionUseCase",
]
