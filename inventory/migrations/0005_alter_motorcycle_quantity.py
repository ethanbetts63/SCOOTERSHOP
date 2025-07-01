                                             

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0004_motorcycle_quantity"),
    ]

    operations = [
        migrations.AlterField(
            model_name="motorcycle",
            name="quantity",
            field=models.IntegerField(
                default=1,
                help_text="Quantity of this motorcycle model in stock. Leave blank for unique used bikes.",
            ),
        ),
    ]
