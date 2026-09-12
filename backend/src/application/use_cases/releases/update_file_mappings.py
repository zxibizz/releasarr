"""Update mappings between release files and media requests."""

from __future__ import annotations

from loguru import logger

from src.application.interfaces.releases import (
    FileMappingUpdateData,
    ReleaseFileMapping,
    ReleaseRepository,
)
from src.application.use_cases.releases.commands import (
    FileMappingCommand,
    UpdateFileMappingsCommand,
)
from src.application.use_cases.releases.exceptions import (
    ReleaseFileNotFoundError,
    ReleaseNotFoundError,
)
from src.domain.enums import MediaType


class UpdateReleaseFileMappingsUseCase:
    """Use case applying mapping changes to release files."""

    def __init__(self, repository: ReleaseRepository) -> None:
        self._repository = repository

    async def execute(self, command: UpdateFileMappingsCommand) -> bool:
        release = await self._repository.get_release(command.release_id)
        if release is None:
            raise ReleaseNotFoundError(command.release_id)

        existing_files = {file_record.id for file_record in release.files}

        updates: list[FileMappingUpdateData] = []
        for file_command in command.files:
            if file_command.file_id not in existing_files:
                raise ReleaseFileNotFoundError(command.release_id, file_command.file_id)

            mapping = self._build_mapping(file_command)
            updates.append(FileMappingUpdateData(file_id=file_command.file_id, mapping=mapping))

        updated = await self._repository.update_file_mappings(command.release_id, updates)
        if not updated:
            raise ReleaseNotFoundError(command.release_id)

        self._log_mappings(command)

        return True

    @staticmethod
    def _log_mappings(command: UpdateFileMappingsCommand) -> None:
        """Record one activity entry per request touched by this mapping change.

        Entries are bound per request id because the /logs endpoint filters on it,
        and a single release can map files to several requests at once.
        """
        mapped_per_request: dict[str, int] = {}
        cleared = 0
        for file_command in command.files:
            if file_command.mapping_type is None or not file_command.request_id:
                cleared += 1
                continue
            mapped_per_request[file_command.request_id] = (
                mapped_per_request.get(file_command.request_id, 0) + 1
            )

        for request_id, count in mapped_per_request.items():
            logger.info(
                f"Mapped {count} release file(s) to this request",
                request_id=request_id,
                release_id=command.release_id,
                file_count=count,
            )

        if cleared:
            logger.info(
                f"Cleared mapping for {cleared} release file(s)",
                release_id=command.release_id,
                file_count=cleared,
            )

    def _build_mapping(self, command: FileMappingCommand) -> ReleaseFileMapping | None:
        if command.mapping_type is None:
            return None
        if not command.request_id:
            raise ValueError("request_id must be provided when mapping a release file")

        media_type = MediaType(command.mapping_type)

        if media_type is MediaType.MOVIE:
            return ReleaseFileMapping(
                mapping_type=media_type,
                request_id=command.request_id,
                request_title=command.request_title,
                season=None,
                episode=None,
            )

        if command.season is None or command.episode is None:
            raise ValueError("season and episode are required for series file mappings")

        return ReleaseFileMapping(
            mapping_type=media_type,
            request_id=command.request_id,
            request_title=command.request_title,
            season=command.season,
            episode=command.episode,
        )


__all__ = ["UpdateReleaseFileMappingsUseCase"]
