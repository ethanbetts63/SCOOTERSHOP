from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        (
            "payments",
            "0006_alter_refundpolicysettings_stripe_fee_fixed_domestic_and_more",
        ),
    ]

    operations = [
        migrations.AlterField(
            model_name="webhookevent",
            name="payload",
            field=models.JSONField(
                blank=True,
                help_text="The full JSON payload of the Stripe webhook event.",
                null=True,
            ),
        ),
    ]
