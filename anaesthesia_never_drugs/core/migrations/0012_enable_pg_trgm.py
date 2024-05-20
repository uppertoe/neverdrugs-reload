# Generated by Django 4.2.10 on 2024-05-20 08:25

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0011_searchindex_search_vector_processed"),
    ]

    operations = [
        migrations.RunSQL(
            sql='CREATE EXTENSION IF NOT EXISTS pg_trgm;',
            reverse_sql='DROP EXTENSION IF EXISTS pg_trgm;',
        ),
    ]
