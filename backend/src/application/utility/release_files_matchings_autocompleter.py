import os
from typing import Iterable

from src.application.models import ReleaseFileMatching


class ReleaseFileMatchingsAutocompleter:
    def autocomplete(self, file_matchings: list[ReleaseFileMatching]) -> None:
        prev_season_number = None
        prev_episode_number = None
        prev_file_dir = None
        prev_file_extension = None

        sorted_file_matchings: Iterable[ReleaseFileMatching] = sorted(
            file_matchings, key=lambda fm: fm.file_name
        )
        for file_matching in sorted_file_matchings:
            season_number = file_matching.season_number
            episode_number = file_matching.episode_number
            file_dir = os.path.dirname(file_matching.file_name)
            file_extension = os.path.splitext(file_matching.file_name)[1]

            if prev_file_dir != file_dir:
                prev_season_number = None
                prev_episode_number = None
                prev_file_extension = None

            if (
                prev_file_extension is not None
                and file_extension != prev_file_extension
                and (not season_number and not episode_number)
            ):
                continue

            if (
                not season_number
                and not episode_number
                and prev_season_number
                and prev_episode_number
            ):
                season_number = prev_season_number
                episode_number = int(prev_episode_number) + 1

            file_matching.season_number = season_number
            file_matching.episode_number = episode_number

            if season_number and episode_number:
                prev_season_number = season_number
                prev_episode_number = episode_number
                prev_file_dir = file_dir
                prev_file_extension = file_extension
