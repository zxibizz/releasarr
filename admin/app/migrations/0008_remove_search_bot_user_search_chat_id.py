# Generated by Django 5.0.6 on 2024-06-16 11:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0007_alter_search_results_alter_search_results_count'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='search',
            name='bot_user',
        ),
        migrations.AddField(
            model_name='search',
            name='chat_id',
            field=models.BigIntegerField(default=1),
            preserve_default=False,
        ),
    ]
