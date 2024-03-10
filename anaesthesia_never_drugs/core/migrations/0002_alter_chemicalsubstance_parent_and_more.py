# Generated by Django 4.2.10 on 2024-03-10 06:20

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="chemicalsubstance",
            name="parent",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="core.chemicaltherapeuticpharmacologicalsubgroup",
            ),
        ),
        migrations.AlterField(
            model_name="chemicaltherapeuticpharmacologicalsubgroup",
            name="parent",
            field=models.ForeignKey(
                null=True, on_delete=django.db.models.deletion.CASCADE, to="core.therapeuticpharmacologicalsubgroup"
            ),
        ),
        migrations.AlterField(
            model_name="therapeuticmaingroup",
            name="parent",
            field=models.ForeignKey(
                null=True, on_delete=django.db.models.deletion.CASCADE, to="core.anatomicalmaingroup"
            ),
        ),
        migrations.AlterField(
            model_name="therapeuticpharmacologicalsubgroup",
            name="parent",
            field=models.ForeignKey(
                null=True, on_delete=django.db.models.deletion.CASCADE, to="core.therapeuticmaingroup"
            ),
        ),
    ]
