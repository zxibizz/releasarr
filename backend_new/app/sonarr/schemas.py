from pydantic import BaseModel


class SonarrEpisode(BaseModel):
    sonarr_episode_id: int
    episode_number: int
    absolute_episode_number: int
    airDateUtc: int
    hasFile: bool
    title: str
