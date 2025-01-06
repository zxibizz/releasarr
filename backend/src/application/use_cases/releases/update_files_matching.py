from pydantic import BaseModel

from src.application.interfaces.db_manager import I_DBManager
from src.application.interfaces.releases_repository import I_ReleasesRepository
from src.application.models import Release
from src.application.utility.release_files_matchings_autocompleter import (
    ReleaseFileMatchingsAutocompleter,
)


class DTO_ReleaseFileMatchingUpdate(BaseModel):
    id: int
    season_number: int | None
    episode_number: int | None


class UseCase_UpdateReleaseFileMatching:
    def __init__(
        self,
        db_manager: I_DBManager,
        releases_repository: I_ReleasesRepository,
        release_files_matching_autocompleter: ReleaseFileMatchingsAutocompleter,
    ) -> None:
        self.db_manager = db_manager
        self.releases_repository = releases_repository
        self.release_files_matching_autocompleter = release_files_matching_autocompleter

    async def process(
        self,
        show_id: int,
        release_name: str,
        updated_file_matchings: list[DTO_ReleaseFileMatchingUpdate],
    ):
        async with self.db_manager.begin_session() as db_session:
            release: Release = await self.releases_repository.get(
                db_session=db_session, name=release_name
            )
            if release.show_id != show_id:
                raise ValueError

            current_file_matchings = sorted(
                release.file_matchings, key=lambda fm: fm.id
            )
            updated_file_matchings = sorted(
                updated_file_matchings, key=lambda fm: fm.id
            )

            if len(current_file_matchings) != len(updated_file_matchings):
                raise ValueError

            for current_file_matching, updated_file_matching in zip(
                current_file_matchings, updated_file_matchings
            ):
                if current_file_matching.id != updated_file_matching.id:
                    raise ValueError

                current_file_matching.season_number = (
                    updated_file_matching.season_number
                )
                current_file_matching.episode_number = (
                    updated_file_matching.episode_number
                )

            self.release_files_matching_autocompleter.autocomplete(
                current_file_matchings
            )

            await self.releases_repository.update_file_matchings(
                db_session, current_file_matchings
            )
