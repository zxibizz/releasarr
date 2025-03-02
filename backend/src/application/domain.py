from datetime import datetime

from pydantic import BaseModel


class SeriesTVDBData(BaseModel):
    titles = list


class Series(BaseModel):
    id: int
    tvdb_data: SeriesTVDBData
    requests: list


class SeriesSeason(BaseModel):
    id: int
    series_id: int
    season_number: int
    is_missing: bool
    episodes: list

    release_searches: list


class SeriesSeasonReleaseSearch(BaseModel):
    series_season_id: int
    is_finished: bool
    episodes: list

    # search in prowlarr
    search_string: str
    prowlarr_search_results: list[dict]

    # pick the best release
    release_choice_prompt: str
    release_choice_result: str

    # get the torrent file
    torrent_infohash: str
    torrent_data: dict

    # map the files of torrent file to the episodes
    files_mapping: dict

    # send the torrent to download client
    grabbed_at: datetime

    # when torrent if finished - manual import to sonarr
    imported_at: datetime
