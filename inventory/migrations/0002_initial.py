                                             

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("inventory", "0001_initial"),
        ("payments", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="salesbooking",
            name="payment",
            field=models.OneToOneField(
                blank=True,
                help_text="Link to the associated payment record, if any (e.g., for deposit).",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="related_sales_booking",
                to="payments.payment",
            ),
        ),
    ]
