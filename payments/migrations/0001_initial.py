import django.db.models.deletion
import django.utils.timezone
import uuid
from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("inventory", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="RefundPolicySettings",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "cancellation_full_payment_full_refund_days",
                    models.PositiveIntegerField(
                        default=7,
                        help_text="Full refund if cancelled this many *full days* or more before the booking's start time (for full payments).",
                    ),
                ),
                (
                    "cancellation_full_payment_partial_refund_days",
                    models.PositiveIntegerField(
                        default=3,
                        help_text="Partial refund if cancelled this many *full days* or more (but less than full refund threshold) before the booking's start time (for full payments).",
                    ),
                ),
                (
                    "cancellation_full_payment_partial_refund_percentage",
                    models.DecimalField(
                        decimal_places=2,
                        default=50.0,
                        help_text="Percentage of total booking price to refund for partial cancellations (for full payments).",
                        max_digits=5,
                    ),
                ),
                (
                    "cancellation_full_payment_minimal_refund_days",
                    models.PositiveIntegerField(
                        default=1,
                        help_text="Minimal refund percentage applies if cancelled this many *full days* or more (but less than partial refund threshold) before the booking's start time (for full payments).",
                    ),
                ),
                (
                    "cancellation_full_payment_minimal_refund_percentage",
                    models.DecimalField(
                        decimal_places=2,
                        default=0.0,
                        help_text="Percentage of total booking price to refund for late cancellations (for full payments).",
                        max_digits=5,
                    ),
                ),
                (
                    "cancellation_deposit_full_refund_days",
                    models.PositiveIntegerField(
                        default=7,
                        help_text="Full refund of deposit if cancelled this many *full days* or more before the booking's start time.",
                    ),
                ),
                (
                    "cancellation_deposit_partial_refund_days",
                    models.PositiveIntegerField(
                        default=3,
                        help_text="Partial refund of deposit if cancelled this many *full days* or more (but less than full refund threshold) before the booking's start time.",
                    ),
                ),
                (
                    "cancellation_deposit_partial_refund_percentage",
                    models.DecimalField(
                        decimal_places=2,
                        default=50.0,
                        help_text="Percentage of deposit to refund for partial cancellations.",
                        max_digits=5,
                    ),
                ),
                (
                    "cancellation_deposit_minimal_refund_days",
                    models.PositiveIntegerField(
                        default=1,
                        help_text="Minimal refund percentage applies to deposit if cancelled this many *full days* or more (but less than partial refund threshold) before the booking's start time.",
                    ),
                ),
                (
                    "cancellation_deposit_minimal_refund_percentage",
                    models.DecimalField(
                        decimal_places=2,
                        default=0.0,
                        help_text="Percentage of deposit to refund for late cancellations.",
                        max_digits=5,
                    ),
                ),
                (
                    "refund_deducts_stripe_fee_policy",
                    models.BooleanField(
                        default=True,
                        help_text="Policy: If true, refunds may have Stripe transaction fees deducted.",
                    ),
                ),
                (
                    "stripe_fee_percentage_domestic",
                    models.DecimalField(
                        decimal_places=4,
                        default=Decimal("0.0170"),
                        help_text="Stripe's percentage fee for domestic cards (e.g., 0.0170 for 1.70%).",
                        max_digits=5,
                    ),
                ),
                (
                    "stripe_fee_fixed_domestic",
                    models.DecimalField(
                        decimal_places=2,
                        default=Decimal("0.30"),
                        help_text="Stripe's fixed fee per transaction for domestic cards (e.g., 0.30 for A$0.30).",
                        max_digits=5,
                    ),
                ),
                (
                    "stripe_fee_percentage_international",
                    models.DecimalField(
                        decimal_places=4,
                        default=Decimal("0.0350"),
                        help_text="Stripe's percentage fee for international cards (e.g., 0.0350 for 3.5%).",
                        max_digits=5,
                    ),
                ),
                (
                    "stripe_fee_fixed_international",
                    models.DecimalField(
                        decimal_places=2,
                        default=Decimal("0.30"),
                        help_text="Stripe's fixed fee per transaction for international cards (e.g., 0.30 for A$0.30).",
                        max_digits=5,
                    ),
                ),
            ],
            options={
                "verbose_name": "Refund Policy Setting",
                "verbose_name_plural": "Refund Policy Settings",
            },
        ),
        migrations.CreateModel(
            name="RefundRequest",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "reason",
                    models.TextField(
                        blank=True,
                        help_text="Customer's reason for requesting the refund.",
                    ),
                ),
                (
                    "rejection_reason",
                    models.TextField(
                        blank=True,
                        help_text="Reason provided by staff for rejecting the refund request.",
                        null=True,
                    ),
                ),
                (
                    "requested_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        help_text="Timestamp when the request was submitted.",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("unverified", "Unverified - Awaiting Email Confirmation"),
                            ("pending", "Pending Review"),
                            (
                                "reviewed_pending_approval",
                                "Reviewed - Pending Approval",
                            ),
                            ("approved", "Approved - Awaiting Refund"),
                            ("rejected", "Rejected"),
                            ("partially_refunded", "Partially Refunded"),
                            ("refunded", "Refunded"),
                            ("failed", "Refund Failed"),
                        ],
                        default="unverified",
                        help_text="Current status of the refund request.",
                        max_length=30,
                    ),
                ),
                (
                    "amount_to_refund",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        help_text="The amount to be refunded, set by staff upon approval (can be partial).",
                        max_digits=10,
                        null=True,
                    ),
                ),
                (
                    "processed_at",
                    models.DateTimeField(
                        blank=True,
                        help_text="Timestamp when the request was processed by staff.",
                        null=True,
                    ),
                ),
                (
                    "staff_notes",
                    models.TextField(
                        blank=True,
                        help_text="Internal notes from staff regarding the processing of this request.",
                    ),
                ),
                (
                    "stripe_refund_id",
                    models.CharField(
                        blank=True,
                        help_text="Stripe Refund ID if the refund was processed via Stripe.",
                        max_length=255,
                        null=True,
                    ),
                ),
                (
                    "is_admin_initiated",
                    models.BooleanField(
                        default=False,
                        help_text="Indicates if this refund request was initiated by an administrator.",
                    ),
                ),
                (
                    "refund_calculation_details",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="Stores a snapshot of details used for refund calculation (e.g., policy applied, original amount, calculated refund amount).",
                    ),
                ),
                (
                    "request_email",
                    models.EmailField(
                        blank=True,
                        help_text="Email address provided by the user for this refund request.",
                        max_length=254,
                        null=True,
                    ),
                ),
                (
                    "verification_token",
                    models.UUIDField(
                        editable=False,
                        help_text="Unique token for email verification of the refund request.",
                        null=True,
                        unique=True,
                    ),
                ),
                (
                    "token_created_at",
                    models.DateTimeField(
                        default=django.utils.timezone.now,
                        help_text="Timestamp when the verification token was created.",
                    ),
                ),
            ],
            options={
                "verbose_name": "Refund Request",
                "verbose_name_plural": "Refund Requests",
                "ordering": ["-requested_at", "pk"],
            },
        ),
        migrations.CreateModel(
            name="WebhookEvent",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "stripe_event_id",
                    models.CharField(
                        db_index=True,
                        help_text="The unique ID of the Stripe webhook event (e.g., 'evt_...').",
                        max_length=100,
                        unique=True,
                    ),
                ),
                (
                    "event_type",
                    models.CharField(
                        help_text="The type of the Stripe event.", max_length=100
                    ),
                ),
                (
                    "received_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        help_text="The timestamp when the webhook event was received and recorded.",
                    ),
                ),
                (
                    "payload",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="The full JSON payload of the Stripe webhook event.",
                        null=True,
                    ),
                ),
            ],
            options={
                "verbose_name": "Stripe Webhook Event",
                "verbose_name_plural": "Stripe Webhook Events",
                "ordering": ["-received_at"],
            },
        ),
        migrations.CreateModel(
            name="Payment",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "stripe_payment_intent_id",
                    models.CharField(
                        blank=True,
                        help_text="The ID of the Stripe Payment Intent object.",
                        max_length=100,
                        null=True,
                        unique=True,
                    ),
                ),
                (
                    "stripe_payment_method_id",
                    models.CharField(
                        blank=True,
                        help_text="The ID of the Stripe Payment Method used for this payment.",
                        max_length=100,
                        null=True,
                    ),
                ),
                (
                    "amount",
                    models.DecimalField(
                        decimal_places=2,
                        help_text="The amount of the payment.",
                        max_digits=10,
                    ),
                ),
                (
                    "currency",
                    models.CharField(
                        default="AUD",
                        help_text="The three-letter ISO currency code (e.g., 'usd', 'AUD').",
                        max_length=3,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        default="requires_payment_method",
                        help_text="The current status of the Stripe Payment Intent (e.g., 'succeeded', 'requires_action').",
                        max_length=50,
                    ),
                ),
                (
                    "description",
                    models.TextField(
                        blank=True,
                        help_text="A description for the payment, often sent to Stripe.",
                        null=True,
                    ),
                ),
                (
                    "metadata",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="Arbitrary key-value pairs for additional payment information or Stripe metadata.",
                    ),
                ),
                (
                    "refund_policy_snapshot",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="Snapshot of refund policy settings from RefundPolicySettings at the time of payment.",
                        null=True,
                    ),
                ),
                (
                    "refunded_amount",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        default=0.0,
                        help_text="The total amount refunded for this payment.",
                        max_digits=10,
                        null=True,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "sales_booking",
                    models.ForeignKey(
                        blank=True,
                        help_text="The permanent sales booking associated with this payment.",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="payments",
                        to="inventory.salesbooking",
                    ),
                ),
                (
                    "sales_customer_profile",
                    models.ForeignKey(
                        blank=True,
                        help_text="The sales customer profile associated with this payment.",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="payments_by_sales_customer",
                        to="inventory.salesprofile",
                    ),
                ),
            ],
            options={
                "verbose_name": "Payment",
                "verbose_name_plural": "Payments",
                "ordering": ["-created_at"],
            },
        ),
    ]
