from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0003_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="refundpolicysettings",
            name="sales_deposit_refund_grace_period_hours",
            field=models.IntegerField(
                default=24,
                help_text="The number of hours within which a deposit can be refunded after cancellation or decline.",
            ),
        ),
        migrations.AddField(
            model_name="refundpolicysettings",
            name="sales_enable_deposit_refund",
            field=models.BooleanField(
                default=True,
                help_text="Globally enable or disable the ability to refund deposits.",
            ),
        ),
        migrations.AddField(
            model_name="refundpolicysettings",
            name="sales_enable_deposit_refund_grace_period",
            field=models.BooleanField(
                default=True,
                help_text="Enable a grace period for deposit refunds after cancellation or decline.",
            ),
        ),
    ]
