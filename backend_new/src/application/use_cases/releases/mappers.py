"""Mapping helpers translating release layer records into DTOs."""

from __future__ import annotations

from src.application.interfaces.releases import (
    QueuedDownload,
    ReleaseFileMapping,
    ReleaseFileRecord,
    ReleaseRecord,
    ReleaseSearchResultRecord,
    ReleaseSearchResults,
)
from src.application.use_cases.releases.dto import (
    AsyncOperationDTO,
    ReleaseDTO,
    ReleaseFileDTO,
    ReleaseFileMappingDTO,
    ReleaseSearchResponseDTO,
    ReleaseSearchResultDTO,
    ReleasesPageDTO,
)


def _mapping_to_dto(mapping: ReleaseFileMapping | None) -> ReleaseFileMappingDTO | None:
    if mapping is None:
        return None

    mapping_type = mapping.mapping_type.value if mapping.mapping_type else None

    return ReleaseFileMappingDTO(
        mapping_type=mapping_type,
        request_id=mapping.request_id,
        request_title=mapping.request_title,
        season=mapping.season,
        episode=mapping.episode,
    )


def _file_record_to_dto(record: ReleaseFileRecord) -> ReleaseFileDTO:
    return ReleaseFileDTO(
        id=record.id,
        name=record.name,
        size_bytes=record.size_bytes,
        path=record.path,
        request_mapping=_mapping_to_dto(record.mapping),
    )


def record_to_dto(record: ReleaseRecord) -> ReleaseDTO:
    files = [_file_record_to_dto(file_record) for file_record in record.files]
    request_ids = list(record.request_ids)

    return ReleaseDTO(
        id=record.id,
        name=record.name,
        info_hash=record.info_hash,
        size_bytes=record.size_bytes,
        files=files,
        status=record.status,
        progress=record.progress,
        download_speed=record.download_speed,
        upload_speed=record.upload_speed,
        seeders=record.seeders,
        leechers=record.leechers,
        ratio=record.ratio,
        added_at=record.added_at,
        completed_at=record.completed_at,
        request_ids=request_ids,
        torrent_source=record.torrent_source,
        quality=record.quality,
    )


def records_to_page(
    records: list[ReleaseRecord],
    *,
    total: int,
    page: int,
    per_page: int,
) -> ReleasesPageDTO:
    releases = [record_to_dto(record) for record in records]
    return ReleasesPageDTO(releases=releases, total=total, page=page, per_page=per_page)


def search_results_to_dto(results: ReleaseSearchResults) -> ReleaseSearchResponseDTO:
    payload = [
        ReleaseSearchResultDTO(
            release_id=result.release_id,
            release_name=result.release_name,
            size=result.size,
            magnet_link=result.magnet_link,
            torrent_file_url=result.torrent_file_url,
            info_url=result.info_url,
            seeders=result.seeders,
            leechers=result.leechers,
            quality=result.quality,
            source=result.source,
            request_id=result.request_id,
        )
        for result in results.results
    ]

    return ReleaseSearchResponseDTO(results=payload, query=results.query, total_results=results.total_results)


def queued_download_to_async_operation(download: QueuedDownload) -> AsyncOperationDTO:
    return AsyncOperationDTO(
        operation=download.operation,
        status=download.status,
        operation_id=download.operation_id,
        location=download.location,
        message=download.message,
        resource_id=download.resource_id,
        details=download.details,
    )


__all__ = [
    "queued_download_to_async_operation",
    "record_to_dto",
    "records_to_page",
    "search_results_to_dto",
]
