from django.db import models


class User(models.Model):
    external_id = models.BigIntegerField()
    first_name = models.TextField()
    last_name = models.TextField()
    username = models.TextField()
    language_code = models.TextField()
