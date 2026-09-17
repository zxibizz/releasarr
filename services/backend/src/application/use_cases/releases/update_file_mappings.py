"""Update mappings between release files and media requests."""

from __future__ import annotations

from src.application.interfaces.releases import (
    FileMappingUpdateData,
    ReleaseFileMapping,
    ReleaseRecord,
    ReleaseRepository,
)
from src.application.interfaces.request_warnings import (
    RequestWarningRecord,
    RequestWarningRepository,
)
from src.application.use_cases.releases.commands import (
    FileMappingCommand,
    UpdateFileMappingsCommand,
)
from src.application.use_cases.releases.exceptions import (
    ReleaseFileNotFoundError,
    ReleaseNotFoundError,
)
from src.application.use_cases.requests.recompute_state import RecomputeRequestStateUseCase
from src.application.use_cases.tasks.enqueue_sync import EnqueueSyncJobUseCase
from src.core.logging import get_logger
from src.domain.enums import (
    LogComponent,
    MediaType,
    ReleaseStatus,
    RequestWarningCode,
    SyncJobKind,
    SyncJobTrigger,
)

_logger = get_logger(LogComponent.USECASE_FILE_MAPPINGS)


class UpdateReleaseFileMappingsUseCase:
    """Use case applying mapping changes to release files."""

    def __init__(
        self,
        repository: ReleaseRepository,
        warning_repository: RequestWarningRepository,
        enqueue_sync: EnqueueSyncJobUseCase,
        recompute_state: RecomputeRequestStateUseCase,
    ) -> None:
        self._repository = repository
        self._warning_repository = warning_repository
        self._enqueue_sync = enqueue_sync
        self._recompute_state = recompute_state

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
        await self._clear_regrab_warning(command.release_id)
        await self._queue_export(release)
        await self._settle_requests(release)

        return True

    async def _clear_regrab_warning(self, release_id: str) -> None:
        """Drop the re-grab "could not map these files" warning once they are placed.

        The warning names the files the replacement torrent added, because only the
        pass that read that torrent knows which files the release did not have
        before; a re-grab is not the only thing that can place them though, so a
        human doing it by hand has to be able to resolve the row too. A save that
        still leaves one of them unmapped is the answer "not yet".
        """

        try:
            rows = await self._warning_repository.list_for_releases([release_id])
            warning = next(
                (
                    row
                    for row in rows.get(release_id, [])
                    if row.code is RequestWarningCode.REGRAB_FILES_UNMAPPED
                ),
                None,
            )
            if warning is None:
                return

            warned = _warned_file_ids(warning)
            if not warned:
                return

            release = await self._repository.get_release(release_id)
            if release is None:
                return

            mapped = {file.id for file in release.files if file.mapping is not None}
            if warned - mapped:
                return

            await self._warning_repository.replace_for_releases(
                RequestWarningCode.REGRAB_FILES_UNMAPPED, [release_id], []
            )
        except Exception as exc:  # pragma: no cover - defensive
            # The mappings are stored either way; a warning outliving them is not
            # worth failing a save over.
            _logger.opt(exception=exc).warning(
                "Failed to clear the re-grab file warning after remapping",
                release_id=release_id,
                error=str(exc),
            )

    async def _settle_requests(self, release: ReleaseRecord) -> None:
        try:
            await self._recompute_state.execute(release.request_ids)
        except Exception as exc:  # pragma: no cover - defensive
            # The mappings already landed; a stale overlap warning or status is
            # not worth failing the request over.
            _logger.opt(exception=exc).warning(
                "Failed to settle requests after remapping",
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

        if release.status is not ReleaseStatus.COMPLETED:
            return

        try:
            await self._enqueue_sync.execute(
                kinds=[SyncJobKind.EXPORT],
                trigger=SyncJobTrigger.API,
            )
        except Exception as exc:
            # The mappings are already stored, so this is not worth failing the
            # request over - the scheduled export run is the fallback.
            _logger.opt(exception=exc).warning(
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
            _logger.info(
                f"Mapped {count} release file(s) to this request",
                request_id=request_id,
                release_id=command.release_id,
                file_count=count,
            )

        for request_id, count in cleared_per_request.items():
            _logger.info(
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


def _warned_file_ids(warning: RequestWarningRecord) -> set[str]:
    """The file ids a re-grab warning named, ignoring anything else in `details`."""

    value = (warning.details or {}).get("file_ids")
    if not isinstance(value, list):
        return set()
    return {item for item in value if isinstance(item, str)}


__all__ = ["UpdateReleaseFileMappingsUseCase"]
