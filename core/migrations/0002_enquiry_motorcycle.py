# Generated by Django 5.2 on 2025-07-05 19:55

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0001_initial"),
        ("inventory", "0015_inventorysettings_enable_sales_enquiries"),
    ]

    operations = [
        migrations.AddField(
            model_name="enquiry",
            name="motorcycle",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="inventory.motorcycle",
            ),
        ),
    ]
