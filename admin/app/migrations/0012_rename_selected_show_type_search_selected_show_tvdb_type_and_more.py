# Generated by Django 5.0.6 on 2024-06-16 18:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0011_rename_selected_show_name_search_selected_show_title'),
    ]

    operations = [
        migrations.RenameField(
            model_name='search',
            old_name='selected_show_type',
            new_name='selected_show_tvdb_type',
        ),
        migrations.AddField(
            model_name='search',
            name='selected_category',
            field=models.TextField(null=True),
        ),
    ]