from app.settings import app_settings
from app.sonarr.client import SonarrApiClient


def get_sonarr_client() -> SonarrApiClient:
    """
    Create and return a SonarrApiClient instance configured with settings from app_settings.
    """
    return SonarrApiClient(
        base_url=app_settings.SONARR_BASE_URL,
        api_token=app_settings.SONARR_API_TOKEN,
    )
