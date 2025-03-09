class TVDBSeries:
    tvdb_series_id: int
    data: dict


class SonarrRequest:
    sonarr_series_id: int
    tvdb_series_id: int
    season_number: int
    is_finished: bool
    is_missing: bool

    episodes: list[dict]
    # {
    #     "sonarr_episode_id": int,
    #     "episode_number": int,
    #     "absolute_episode_number": int,
    #     "airDateUtc": int,
    #     "hasFile": bool,
    #     "title": str,
    # }

    prowlarr_manual_search_string: str
    # prowlarr_search_results: list[dict]  # Store in cache

    # All this info is needed to regrab the updated release
    prowlarr_release_search_string: str
    prowlarr_release_title: str
    prowlarr_release_info_url: str
    prowlarr_release_size: int

    torrent_guid: str
    torrent_data: str
    torrent_is_finished: bool
    torrent_files_matching: list[dict]

    # Avoid importing the same torrent twice to Sonarr
    last_imported_torrent_guid: str
