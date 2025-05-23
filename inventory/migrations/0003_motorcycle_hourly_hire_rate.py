# Generated by Django 5.1.6 on 2025-05-16 15:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0002_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="motorcycle",
            name="hourly_hire_rate",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="Price per hour for hiring (if applicable)",
                max_digits=8,
                null=True,
            ),
        ),
    ]
