from django.db import models


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
