import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        
    ]

    operations = [
        migrations.CreateModel(
            name="EmailLog",
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
                    "timestamp",
                    models.DateTimeField(
                        default=django.utils.timezone.now,
                        help_text="The date and time the email was attempted to be sent.",
                    ),
                ),
                (
                    "sender",
                    models.CharField(
                        help_text="The email address from which the email was sent.",
                        max_length=255,
                    ),
                ),
                (
                    "recipient",
                    models.CharField(
                        help_text="The primary recipient's email address.",
                        max_length=255,
                    ),
                ),
                (
                    "subject",
                    models.CharField(
                        help_text="The subject line of the email.", max_length=255
                    ),
                ),
                (
                    "body",
                    models.TextField(
                        help_text="The full content (HTML or plain text) of the email body."
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("SENT", "Sent"),
                            ("FAILED", "Failed"),
                            ("PENDING", "Pending"),
                        ],
                        default="PENDING",
                        help_text="The sending status of the email (e.g., Sent, Failed, Pending).",
                        max_length=10,
                    ),
                ),
                (
                    "error_message",
                    models.TextField(
                        blank=True,
                        help_text="Any error message if the email sending failed.",
                        null=True,
                    ),
                ),
                
            ],
            options={
                "verbose_name": "Email Log",
                "verbose_name_plural": "Email Logs",
                "ordering": ["-timestamp"],
            },
        ),
    ]