"""Update mappings between release files and media requests."""

from __future__ import annotations

from loguru import logger

from src.application.interfaces.releases import (
    FileMappingUpdateData,
    ReleaseFileMapping,
    ReleaseRecord,
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
from src.application.use_cases.releases.warnings import RequestWarningSynchronizer
from src.application.use_cases.tasks.enqueue_sync import EnqueueSyncJobUseCase
from src.domain.enums import MediaType, ReleaseStatus, SyncJobKind, SyncJobTrigger


class UpdateReleaseFileMappingsUseCase:
    """Use case applying mapping changes to release files."""

    def __init__(
        self,
        repository: ReleaseRepository,
        enqueue_sync: EnqueueSyncJobUseCase | None = None,
        warning_synchronizer: RequestWarningSynchronizer | None = None,
    ) -> None:
        self._repository = repository
        self._enqueue_sync = enqueue_sync
        self._warning_synchronizer = warning_synchronizer

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

        # Re-arm the release for export. Remapping is how a wrong or incomplete
        # import gets corrected, so the export has to run again on what is now a
        # different set of files - and a run that exhausted its retries deserves
        # a fresh budget, since the mapping change is the fix for it.
        await self._repository.update_release(
            command.release_id,
            last_exported_info_hash=None,
            export_failures_count=0,
        )

        self._log_mappings(command, release)
        await self._queue_export(release)
        await self._sync_warnings(release)

        return True

    async def _sync_warnings(self, release: ReleaseRecord) -> None:
        if self._warning_synchronizer is None:
            return
        try:
            await self._warning_synchronizer.sync_for_requests(release.request_ids)
        except Exception as exc:  # pragma: no cover - defensive
            # The mappings already landed; a stale overlap warning is not worth
            # failing the request over.
            logger.opt(exception=exc).warning(
                "Failed to recompute mapping overlap warnings",
                release_id=release.id,
                error=str(exc),
            )

    async def _queue_export(self, release: ReleaseRecord) -> None:
        """Run the export again for a release that already finished downloading.

        Re-arming the release is not enough on its own: the export only revisits
        it when a run happens, and the next scheduled one is minutes away, so the
        correction the user just made would sit unapplied until then. A release
        still downloading needs nothing, since the export skips it either way and
        the run that follows its completion picks the new mapping up.
        """

        if self._enqueue_sync is None or release.status is not ReleaseStatus.COMPLETED:
            return

        try:
            await self._enqueue_sync.execute(
                kinds=[SyncJobKind.EXPORT],
                trigger=SyncJobTrigger.API,
            )
        except Exception as exc:
            # The mappings are already stored, so this is not worth failing the
            # request over - the scheduled export run is the fallback.
            logger.opt(exception=exc).warning(
                "Could not queue an export for the remapped release",
                release_id=release.id,
                error=str(exc),
            )

    @staticmethod
    def _log_mappings(command: UpdateFileMappingsCommand, release: ReleaseRecord) -> None:
        """Record one activity entry per request touched by this mapping change.

        Entries are bound per request id because the /logs endpoint filters on it,
        and a single release can map files to several requests at once. A file
        taken away is attributed to whoever held it before the change, which is
        the request the removal is news for; ``release`` was read before the
        update, so it still carries those owners.
        """
        previous_owner = {
            file.id: file.mapping.request_id
            for file in release.files
            if file.mapping and file.mapping.request_id
        }
        mapped_per_request: dict[str, int] = {}
        cleared_per_request: dict[str, int] = {}
        for file_command in command.files:
            new_owner = (
                file_command.request_id
                if file_command.mapping_type is not None and file_command.request_id
                else None
            )
            if new_owner:
                mapped_per_request[new_owner] = mapped_per_request.get(new_owner, 0) + 1

            owner = previous_owner.get(file_command.file_id)
            if owner and owner != new_owner:
                cleared_per_request[owner] = cleared_per_request.get(owner, 0) + 1

        for request_id, count in mapped_per_request.items():
            logger.info(
                f"Mapped {count} release file(s) to this request",
                request_id=request_id,
                release_id=command.release_id,
                file_count=count,
            )

        for request_id, count in cleared_per_request.items():
            logger.info(
                f"Unmapped {count} release file(s) from this request",
                request_id=request_id,
                release_id=command.release_id,
                file_count=count,
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
