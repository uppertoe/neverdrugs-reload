# Generated by Django 4.2.10 on 2024-05-19 04:37

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0004_anatomicalmaingroup_unique_anatomical_main_group_and_more"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="searchindex",
            options={"verbose_name_plural": "search indices"},
        ),
        migrations.AlterField(
            model_name="drugcategory",
            name="category",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="drug_categories",
                to="core.chemicalsubstance",
            ),
        ),
    ]
