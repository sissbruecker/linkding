# Generated by Django 5.0.3 on 2024-05-17 07:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("bookmarks", "0036_userprofile_auto_tagging_rules"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="tag_hierarchy",
            field=models.BooleanField(default=False),
        ),
    ]