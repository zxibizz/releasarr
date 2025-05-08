from app.settings import app_settings
from app.tvdb.client import TVDBApiClient


def get_tvdb_client() -> TVDBApiClient:
    """
    Create and return a TVDBApiClient instance configured with settings from app_settings.
    """
    return TVDBApiClient(api_token=app_settings.TVDB_API_TOKEN)
