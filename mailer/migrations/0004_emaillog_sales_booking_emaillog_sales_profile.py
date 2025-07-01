                                             

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0005_alter_motorcycle_quantity"),
        ("mailer", "0003_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="emaillog",
            name="sales_booking",
            field=models.ForeignKey(
                blank=True,
                help_text="The sales booking associated with this email, if applicable.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="related_emails_for_sales",
                to="inventory.salesbooking",
            ),
        ),
        migrations.AddField(
            model_name="emaillog",
            name="sales_profile",
            field=models.ForeignKey(
                blank=True,
                help_text="The sales profile associated with this email, if applicable.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="sent_emails_for_sales_profile",
                to="inventory.salesprofile",
            ),
        ),
    ]
