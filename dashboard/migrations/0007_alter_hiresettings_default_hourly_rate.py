# Generated by Django 5.2 on 2025-05-24 18:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dashboard", "0006_alter_hiresettings_currency_symbol"),
    ]

    operations = [
        migrations.AlterField(
            model_name="hiresettings",
            name="default_hourly_rate",
            field=models.DecimalField(
                decimal_places=2,
                default=0.0,
                help_text="Default hourly rate for bikes if no custom rate is set (optional).",
                max_digits=8,
            ),
        ),
    ]
