from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0003_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="motorcycle",
            name="quantity",
            field=models.IntegerField(
                blank=True,
                help_text="Quantity of this motorcycle model in stock. Leave blank for unique used bikes.",
                null=True,
            ),
        ),
    ]
