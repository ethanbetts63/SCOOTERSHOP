##


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0008_salesfaq"),
    ]

    operations = [
        migrations.AddField(
            model_name="motorcycle",
            name="is_available",
            field=models.BooleanField(
                default=True, help_text="Is this bike generally available for sale?"
            ),
        ),
        migrations.AlterField(
            model_name="motorcycle",
            name="conditions",
            field=models.ManyToManyField(
                blank=True,
                help_text="Select all applicable conditions (e.g., Used, New, Demo.)",
                related_name="motorcycles",
                to="inventory.motorcyclecondition",
            ),
        ),
    ]
