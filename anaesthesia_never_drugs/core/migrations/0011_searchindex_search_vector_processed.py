# Generated by Django 4.2.10 on 2024-05-20 00:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0010_condition_searchable_alter_condition_orpha_code"),
    ]

    operations = [
        migrations.AddField(
            model_name="searchindex",
            name="search_vector_processed",
            field=models.BooleanField(default=False),
        ),
    ]