# Generated by Django 5.2 on 2025-05-21 20:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dashboard", "0004_hiresettings_enable_card_payment_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="hiresettings",
            name="enable_cash_payment",
            field=models.BooleanField(
                default=False, help_text="Allow customers to pay with cash in store."
            ),
        ),
    ]
