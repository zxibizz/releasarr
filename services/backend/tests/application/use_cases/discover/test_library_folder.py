"""Tests for reading and moving the root folder a request's media is stored in."""

from __future__ import annotations

import pytest

from src.application.interfaces.arr import ArrRootFolder
from src.application.use_cases.discover.exceptions import (
    DisallowedRootFolderError,
    InvalidRootFolderError,
    LibraryFolderUnavailableError,
)
from src.application.use_cases.discover.library_folder import (
    GetLibraryFolderUseCase,
    MoveLibraryFolderCommand,
    MoveLibraryFolderUseCase,
)
from src.application.use_cases.requests.exceptions import MediaRequestNotFoundError
from src.domain.enums import MediaType
from tests.fakes import (
    FakeMediaRequestRepository,
    FakeRadarrService,
    FakeSonarrService,
    make_movie_details,
    make_record,
    make_series_details,
)

SERIES_FOLDERS = [
    ArrRootFolder(path="/Media/TV Shows/", free_space=1024),
    ArrRootFolder(path="/Media/Anime Series/", free_space=1024),
    ArrRootFolder(path="/Media/Archive/", accessible=False),
]


def series_sonarr(path: str = "/Media/TV Shows/Example Show", root: str | None = None):
    details = make_series_details(12)
    details.path = path
    details.root_folder_path = root
    return FakeSonarrService(catalogue={12: details}, root_folders=list(SERIES_FOLDERS))


def series_repository() -> FakeMediaRequestRepository:
    return FakeMediaRequestRepository(
        {"req-1": make_record("req-1", season_number=1, sonarr_series_id=12)}
    )


def build_move(
    repository: FakeMediaRequestRepository,
    sonarr: FakeSonarrService,
    radarr: FakeRadarrService | None = None,
) -> MoveLibraryFolderUseCase:
    return MoveLibraryFolderUseCase(
        repository=repository,
        sonarr_service=sonarr,
        radarr_service=radarr or FakeRadarrService(),
    )


@pytest.mark.asyncio
async def test_the_current_folder_is_spelled_as_the_root_folder_list_spells_it() -> None:
    """Sonarr's own root folder may lack the trailing slash the list carries."""

    result = await GetLibraryFolderUseCase(
        repository=series_repository(),
        sonarr_service=series_sonarr(root="/Media/TV Shows"),
        radarr_service=FakeRadarrService(),
    ).execute("req-1")

    assert result.media_type == MediaType.SERIES
    assert result.path == "/Media/TV Shows/Example Show"
    assert result.root_folder_path == "/Media/TV Shows/"


@pytest.mark.asyncio
async def test_the_current_folder_is_worked_out_from_the_path_when_not_reported() -> None:
    result = await GetLibraryFolderUseCase(
        repository=series_repository(),
        sonarr_service=series_sonarr(path="/Media/Anime Series/Example Show"),
        radarr_service=FakeRadarrService(),
    ).execute("req-1")

    assert result.root_folder_path == "/Media/Anime Series/"


@pytest.mark.asyncio
async def test_a_series_is_moved_to_the_picked_folder() -> None:
    sonarr = series_sonarr()

    result = await build_move(series_repository(), sonarr).execute(
        "req-1", MoveLibraryFolderCommand(root_folder_path="/Media/Anime Series/")
    )

    assert sonarr.moved == [(12, "/Media/Anime Series/")]
    assert result.root_folder_path == "/Media/Anime Series/"
    assert result.path == "/Media/Anime Series/Example Show"


@pytest.mark.asyncio
async def test_moving_to_the_folder_it_is_already_in_changes_nothing() -> None:
    sonarr = series_sonarr()

    result = await build_move(series_repository(), sonarr).execute(
        "req-1", MoveLibraryFolderCommand(root_folder_path="/Media/TV Shows")
    )

    assert sonarr.moved == []
    assert result.root_folder_path == "/Media/TV Shows/"


@pytest.mark.asyncio
async def test_a_movie_is_moved_through_radarr() -> None:
    details = make_movie_details(31)
    details.path = "/movies/Example Movie (2021)"
    radarr = FakeRadarrService(
        catalogue={31: details},
        root_folders=[ArrRootFolder(path="/movies"), ArrRootFolder(path="/anime-movies")],
    )
    repository = FakeMediaRequestRepository(
        {"req-1": make_record("req-1", media_type=MediaType.MOVIE, radarr_movie_id=31)}
    )

    result = await build_move(repository, FakeSonarrService(), radarr).execute(
        "req-1", MoveLibraryFolderCommand(root_folder_path="/anime-movies")
    )

    assert radarr.moved == [(31, "/anime-movies")]
    assert result.media_type == MediaType.MOVIE
    assert result.path == "/anime-movies/Example Movie (2021)"


@pytest.mark.asyncio
@pytest.mark.parametrize("folder", ["/Media/Nowhere/", "/Media/Archive/"])
async def test_only_a_configured_reachable_folder_can_be_moved_to(folder: str) -> None:
    sonarr = series_sonarr()

    with pytest.raises(InvalidRootFolderError):
        await build_move(series_repository(), sonarr).execute(
            "req-1", MoveLibraryFolderCommand(root_folder_path=folder)
        )

    assert sonarr.moved == []


@pytest.mark.asyncio
async def test_a_restricted_caller_may_not_move_to_a_folder_outside_their_list() -> None:
    sonarr = series_sonarr()

    with pytest.raises(DisallowedRootFolderError):
        await build_move(series_repository(), sonarr).execute(
            "req-1",
            MoveLibraryFolderCommand(
                root_folder_path="/Media/Anime Series/",
                allowed_root_folders=["/Media/TV Shows/"],
            ),
        )

    assert sonarr.moved == []


@pytest.mark.asyncio
async def test_a_restricted_caller_may_not_take_a_title_out_of_a_folder_outside_their_list() -> (
    None
):
    sonarr = series_sonarr()

    with pytest.raises(DisallowedRootFolderError):
        await build_move(series_repository(), sonarr).execute(
            "req-1",
            MoveLibraryFolderCommand(
                root_folder_path="/Media/Anime Series/",
                allowed_root_folders=["/Media/Anime Series/"],
            ),
        )

    assert sonarr.moved == []


@pytest.mark.asyncio
async def test_a_restricted_caller_allowed_both_folders_can_move() -> None:
    sonarr = series_sonarr()

    await build_move(series_repository(), sonarr).execute(
        "req-1",
        MoveLibraryFolderCommand(
            root_folder_path="/Media/Anime Series/",
            allowed_root_folders=["/Media/TV Shows/", "/Media/Anime Series/"],
        ),
    )

    assert sonarr.moved == [(12, "/Media/Anime Series/")]


@pytest.mark.asyncio
async def test_a_request_sonarr_has_not_linked_yet_has_nothing_to_move() -> None:
    repository = FakeMediaRequestRepository({"req-1": make_record("req-1", season_number=1)})

    with pytest.raises(LibraryFolderUnavailableError):
        await build_move(repository, series_sonarr()).execute(
            "req-1", MoveLibraryFolderCommand(root_folder_path="/Media/Anime Series/")
        )


@pytest.mark.asyncio
async def test_an_unknown_request_is_not_found() -> None:
    with pytest.raises(MediaRequestNotFoundError):
        await GetLibraryFolderUseCase(
            repository=FakeMediaRequestRepository(),
            sonarr_service=series_sonarr(),
            radarr_service=FakeRadarrService(),
        ).execute("missing")
