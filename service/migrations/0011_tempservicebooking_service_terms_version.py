# Generated by Django 5.2 on 2025-07-05 14:39

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("service", "0010_alter_serviceterms_content"),
    ]

    operations = [
        migrations.AddField(
            model_name="tempservicebooking",
            name="service_terms_version",
            field=models.ForeignKey(
                blank=True,
                help_text="The specific version of the Service T&Cs the user agreed to.",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="temp_service_bookings",
                to="service.serviceterms",
            ),
        ),
    ]
