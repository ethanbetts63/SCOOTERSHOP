                                             

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0006_inventorysettings_send_sales_booking_to_mechanic_desk"),
    ]

    operations = [
        migrations.AlterField(
            model_name="motorcycle",
            name="status",
            field=models.CharField(
                choices=[
                    ("for_sale", "For Sale"),
                    ("sold", "Sold"),
                    ("reserved", "Reserved"),
                    ("for_hire", "For Hire"),
                    ("unavailable", "Unavailable"),
                ],
                default="for_sale",
                help_text="The sales/hire status of the motorcycle.",
                max_length=20,
            ),
        ),
    ]
