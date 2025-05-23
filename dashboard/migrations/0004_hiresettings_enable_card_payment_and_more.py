# Generated by Django 5.2 on 2025-05-21 11:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dashboard", "0003_remove_hiresettings_default_monthly_rate_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="hiresettings",
            name="enable_card_payment",
            field=models.BooleanField(
                default=False, help_text="Allow customers to pay with card in store."
            ),
        ),
        migrations.AddField(
            model_name="hiresettings",
            name="enable_cash_payment",
            field=models.BooleanField(
                default=False, help_text="Allow customers to pay with cash."
            ),
        ),
        migrations.AddField(
            model_name="hiresettings",
            name="enable_in_store_full_payment",
            field=models.BooleanField(
                default=False,
                help_text="Allow customers to pay the full amount in store.",
            ),
        ),
        migrations.AddField(
            model_name="hiresettings",
            name="enable_online_deposit_payment",
            field=models.BooleanField(
                default=False, help_text="Allow customers to pay a deposit online."
            ),
        ),
        migrations.AddField(
            model_name="hiresettings",
            name="enable_online_full_payment",
            field=models.BooleanField(
                default=False,
                help_text="Allow customers to pay the full amount online.",
            ),
        ),
        migrations.AddField(
            model_name="hiresettings",
            name="enable_other_payment",
            field=models.BooleanField(
                default=False, help_text="Allow other payment methods."
            ),
        ),
    ]
