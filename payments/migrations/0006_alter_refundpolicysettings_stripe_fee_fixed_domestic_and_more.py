                                             

from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0005_refundrequest_sales_booking_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="refundpolicysettings",
            name="stripe_fee_fixed_domestic",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("0.30"),
                help_text="Stripe's fixed fee per transaction for domestic cards (e.30 for A$0.30).",
                max_digits=5,
            ),
        ),
        migrations.AlterField(
            model_name="refundpolicysettings",
            name="stripe_fee_fixed_international",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("0.30"),
                help_text="Stripe's fixed fee per transaction for international cards (e.30 for A$0.30).",
                max_digits=5,
            ),
        ),
    ]
