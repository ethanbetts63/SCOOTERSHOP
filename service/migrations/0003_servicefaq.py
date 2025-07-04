from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("service", "0002_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ServiceFAQ",
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
                            ("service_page", "Main Service Page"),
                            ("step1", "Step 1: Service Details"),
                            ("step2", "Step 2: Motorcycle Selection"),
                            ("step3", "Step 3: Your Motorcycle Details"),
                            ("step4", "Step 4: Your Profile"),
                            ("step5", "Step 5: Dropoff & Terms"),
                            ("step6", "Step 6: Payment"),
                            ("step7", "Step 7: Confirmation"),
                            ("general", "General Service Pages"),
                        ],
                        help_text="The step in the service booking process where this FAQ should be displayed.",
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
                "verbose_name": "Service FAQ",
                "verbose_name_plural": "Service FAQs",
                "ordering": ["booking_step", "display_order", "question"],
            },
        ),
    ]
