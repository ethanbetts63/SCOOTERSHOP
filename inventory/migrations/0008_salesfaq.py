                                             

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0007_alter_motorcycle_status"),
    ]

    operations = [
        migrations.CreateModel(
            name="SalesFAQ",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "booking_step",
                    models.CharField(
                        choices=[
                            ("step1", "Step 1: Your Details"),
                            ("step2", "Step 2: Booking Details & Appointment"),
                            ("step3", "Step 3: Payment"),
                            ("step4", "Step 4: Confirmation"),
                            ("general", "General Sales Pages"),
                        ],
                        help_text="The step in the booking process where this FAQ should be displayed.",
                        max_length=20,
                    ),
                ),
                (
                    "question",
                    models.CharField(
                        help_text="The frequently asked question.", max_length=255
                    ),
                ),
                ("answer", models.TextField(help_text="The answer to the question.")),
                (
                    "is_active",
                    models.BooleanField(
                        default=True,
                        help_text="Designates whether this FAQ is publicly visible.",
                    ),
                ),
                (
                    "display_order",
                    models.PositiveIntegerField(
                        default=0,
                        help_text="The order in which the FAQ appears. Lower numbers are displayed first.",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Sales FAQ",
                "verbose_name_plural": "Sales FAQs",
                "ordering": ["booking_step", "display_order", "question"],
            },
        ),
    ]
