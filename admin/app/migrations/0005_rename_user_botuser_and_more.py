# Generated by Django 5.0.6 on 2024-06-15 19:56

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0004_rename_user_id_user_external_id'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='User',
            new_name='BotUser',
        ),
        migrations.RenameField(
            model_name='botuser',
            old_name='external_id',
            new_name='chat_id',
        ),
    ]
