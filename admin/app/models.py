from django.db import models
from django_pydantic_field import SchemaField

from bot.dependencies.prowlarr import ProwlarrRelease, ProwlarrTorrentMeta


class BotUser(models.Model):
    chat_id = models.BigIntegerField()
    first_name = models.TextField()
    last_name = models.TextField()
    username = models.TextField()
    language_code = models.TextField()


class Search(models.Model):
    chat_id = models.BigIntegerField()
    query = models.TextField()
    image_message_id = models.BigIntegerField(null=True)
    content_message_id = models.BigIntegerField(null=True)
    results = models.JSONField(null=True)
    results_count = models.BigIntegerField(null=True)
    status = models.TextField()
    selected_show_tvdb_id = models.BigIntegerField(null=True)
    selected_show_tvdb_type = models.TextField(null=True)
    selected_show_title = models.TextField(null=True)
    selected_category = models.TextField(null=True)
    seasons_data = models.JSONField(null=True)
    selected_season = models.IntegerField(null=True)
    found_releases = models.JSONField(null=True)
    selected_release_guid = models.TextField(null=True)


class SonarrSeries(models.Model):
    series_id = models.BigIntegerField(unique=True)
    path = models.FilePathField()
    tvdb_id = models.BigIntegerField(null=True)
    tvdb_year = models.TextField(null=True)
    tvdb_country = models.TextField(null=True)
    tvdb_title = models.TextField(null=True)
    tvdb_title_en = models.TextField(null=True)
    tvdb_image_url = models.TextField(null=True)
    tvdb_overview = models.TextField(null=True)


class SonarrMonitoredSeason(models.Model):
    season_number = models.IntegerField()
    episode_file_count = models.IntegerField()
    episode_count = models.IntegerField()
    total_episodes_count = models.IntegerField()
    previous_airing = models.DateTimeField(null=True)
    series = models.ForeignKey(
        SonarrSeries,
        to_field="series_id",
        on_delete=models.DO_NOTHING,
        related_name="seasons",
    )
    current_select = models.ForeignKey(
        "SonarrReleaseSelect", on_delete=models.CASCADE, null=True
    )
    current_download = models.ForeignKey(
        "SonarrDownload", on_delete=models.CASCADE, null=True
    )


class SonarrReleaseSelect(models.Model):
    season = models.ForeignKey(SonarrMonitoredSeason, models.CASCADE)
    prowlarr_results: list[ProwlarrRelease] = SchemaField(schema=list[ProwlarrRelease])
    chat_id = models.BigIntegerField()
    select_message_id = models.BigIntegerField(null=True)
    is_finished = models.BooleanField(default=False)


class SonarrDownload(models.Model):
    season = models.ForeignKey(SonarrMonitoredSeason, on_delete=models.CASCADE)
    prowlarr_torrent_meta: "ProwlarrTorrentMeta" = SchemaField(
        schema=ProwlarrTorrentMeta
    )
    prowlarr_torrent_data = models.BinaryField()
    prowlarr_indexer_id = models.BigIntegerField()
    prowlarr_guid = models.TextField()
    episode_count = models.IntegerField()
    is_finished = models.BooleanField(default=False)
