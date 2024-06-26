# Generated by Django 4.2.10 on 2024-05-23 02:24

import django.contrib.postgres.indexes
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0014_change_gist_to_gin"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="searchindex",
            index=django.contrib.postgres.indexes.GinIndex(
                fields=["name"], name="name_gin_trgm_idx", opclasses=["gin_trgm_ops"]
            ),
        ),
    ]
