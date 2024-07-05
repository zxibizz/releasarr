from django.db import models


class BotUser(models.Model):
    chat_id = models.BigIntegerField()
    first_name = models.TextField()
    last_name = models.TextField()
    username = models.TextField()
    language_code = models.TextField()


class Search(models.Model):
    bot_user = models.ForeignKey(BotUser, on_delete=models.CASCADE)
    query = models.TextField()
    image_message_id = models.BigIntegerField(null=True)
    content_message_id = models.BigIntegerField(null=True)
    results = models.JSONField(null=True)
    results_count = models.BigIntegerField(null=True)
    status = models.TextField()
