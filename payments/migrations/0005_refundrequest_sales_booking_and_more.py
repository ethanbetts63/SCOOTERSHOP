import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0005_alter_motorcycle_quantity"),
        (
            "payments",
            "0004_refundpolicysettings_sales_deposit_refund_grace_period_hours_and_more",
        ),
    ]

    operations = [
        migrations.AddField(
            model_name="refundrequest",
            name="sales_booking",
            field=models.ForeignKey(
                blank=True,
                help_text="The sales booking for which the refund is requested (if applicable).",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="refund_requests",
                to="inventory.salesbooking",
            ),
        ),
        migrations.AddField(
            model_name="refundrequest",
            name="sales_profile",
            field=models.ForeignKey(
                blank=True,
                help_text="The sales profile associated with this refund request (if applicable).",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="refund_requests_related_sales_profile",
                to="inventory.salesprofile",
            ),
        ),
    ]
