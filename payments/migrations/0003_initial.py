import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("payments", "0002_initial"),
        ("service", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="refundrequest",
            name="processed_by",
            field=models.ForeignKey(
                blank=True,
                help_text="Staff member who processed this request.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="processed_refund_requests",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="refundrequest",
            name="service_booking",
            field=models.ForeignKey(
                blank=True,
                help_text="The service booking for which the refund is requested (if applicable).",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="refund_requests",
                to="service.servicebooking",
            ),
        ),
        migrations.AddField(
            model_name="refundrequest",
            name="service_profile",
            field=models.ForeignKey(
                blank=True,
                help_text="The service profile associated with this refund request (if applicable).",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="refund_requests_related_service_profile",
                to="service.serviceprofile",
            ),
        ),
    ]
