                                             

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0005_alter_motorcycle_quantity"),
    ]

    operations = [
        migrations.AddField(
            model_name="inventorysettings",
            name="send_sales_booking_to_mechanic_desk",
            field=models.BooleanField(
                default=False,
                help_text="Automatically send sales booking details to the mechanic's desk upon confirmation.",
            ),
        ),
    ]
