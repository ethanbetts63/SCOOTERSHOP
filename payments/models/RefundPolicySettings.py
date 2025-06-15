# payments/models/refund_policy_settings.py

from django.db import models
from django.core.exceptions import ValidationError
from decimal import Decimal

class RefundPolicySettings(models.Model):
    """
    Centralized settings for refund policies and Stripe fees across all booking types.
    This model is designed to be a singleton; only one instance should exist.
    """

    # --- Full Payment Cancellation Policy (matching HireSettings conventions) ---
    cancellation_full_payment_full_refund_days = models.PositiveIntegerField(
        default=7,
        help_text="Full refund if cancelled this many *full days* or more before the booking's start time (for full payments)."
    )
    cancellation_full_payment_partial_refund_days = models.PositiveIntegerField(
        default=3,
        help_text="Partial refund if cancelled this many *full days* or more (but less than full refund threshold) before the booking's start time (for full payments)."
    )
    cancellation_full_payment_partial_refund_percentage = models.DecimalField(
        max_digits=5, decimal_places=2,
        default=50.00, # e.g., 50.00 for 50%
        help_text="Percentage of total booking price to refund for partial cancellations (for full payments)."
    )
    cancellation_full_payment_minimal_refund_days = models.PositiveIntegerField(
         default=1,
         help_text="Minimal refund percentage applies if cancelled this many *full days* or more (but less than partial refund threshold) before the booking's start time (for full payments)."
    )
    cancellation_full_payment_minimal_refund_percentage = models.DecimalField(
        max_digits=5, decimal_places=2,
        default=0.00, # e.g., 0.00 for 0%
        help_text="Percentage of total booking price to refund for late cancellations (for full payments)."
    )

    # --- Deposit Cancellation Policy (matching HireSettings conventions) ---
    cancellation_deposit_full_refund_days = models.PositiveIntegerField(
        default=7,
        help_text="Full refund of deposit if cancelled this many *full days* or more before the booking's start time."
    )
    cancellation_deposit_partial_refund_days = models.PositiveIntegerField(
        default=3,
        help_text="Partial refund of deposit if cancelled this many *full days* or more (but less than full refund threshold) before the booking's start time."
    )
    cancellation_deposit_partial_refund_percentage = models.DecimalField(
        max_digits=5, decimal_places=2,
        default=50.00, # e.g., 50.00 for 50%
        help_text="Percentage of deposit to refund for partial cancellations."
    )
    cancellation_deposit_minimal_refund_days = models.PositiveIntegerField(
         default=1,
         help_text="Minimal refund percentage applies to deposit if cancelled this many *full days* or more (but less than partial refund threshold) before the booking's start time."
    )
    cancellation_deposit_minimal_refund_percentage = models.DecimalField(
        max_digits=5, decimal_places=2,
        default=0.00, # e.g., 0.00 for 0%
        help_text="Percentage of deposit to refund for late cancellations."
    )

    # --- Inventory app refund settings
    sales_enable_deposit_refund_grace_period = models.BooleanField(
        default=True,
        help_text="Enable a grace period for deposit refunds after cancellation or decline."
    )
    sales_deposit_refund_grace_period_hours = models.IntegerField(
        default=24, # 48 hours (2 days)
        help_text="The number of hours within which a deposit can be refunded after cancellation or decline."
    )
    sales_enable_deposit_refund = models.BooleanField(
        default=True,
        help_text="Globally enable or disable the ability to refund deposits."
    )


    # --- Stripe Fee Settings ---
    refund_deducts_stripe_fee_policy = models.BooleanField(
        default=True,
        help_text="Policy: If true, refunds may have Stripe transaction fees deducted."
    )
    stripe_fee_percentage_domestic = models.DecimalField(
        max_digits=5, decimal_places=4, default=Decimal('0.0170'),
        help_text="Stripe's percentage fee for domestic cards (e.g., 0.0170 for 1.70%)."
    )
    stripe_fee_fixed_domestic = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('0.30'),
        help_text="Stripe's fixed fee per transaction for domestic cards (e.g., 0.30 for A$0.30)."
    )
    stripe_fee_percentage_international = models.DecimalField(
        max_digits=5, decimal_places=4, default=Decimal('0.0350'),
        help_text="Stripe's percentage fee for international cards (e.g., 0.0350 for 3.5%)."
    )
    stripe_fee_fixed_international = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('0.30'),
        help_text="Stripe's fixed fee per transaction for international cards (e.g., 0.30 for A$0.30)."
    )

    def __str__(self):
        return "Refund Policy Settings"

    def clean(self):
        errors = {}

        # Validate percentage fields (0.00 to 100.00)
        percentage_fields = [
            'cancellation_full_payment_partial_refund_percentage',
            'cancellation_full_payment_minimal_refund_percentage',
            'cancellation_deposit_partial_refund_percentage',
            'cancellation_deposit_minimal_refund_percentage',
        ]
        for field_name in percentage_fields:
            value = getattr(self, field_name)
            if value is not None and not (Decimal('0.00') <= value <= Decimal('100.00')):
                errors[field_name] = [f"Ensure {field_name.replace('_', ' ')} is between 0.00% and 100.00%."]

        # Validate Stripe fee percentages (0.00 to 0.10 for 0-10%)
        if self.stripe_fee_percentage_domestic is not None and not (Decimal('0.00') <= self.stripe_fee_percentage_domestic <= Decimal('0.10')):
            errors['stripe_fee_percentage_domestic'] = ["Ensure domestic Stripe fee percentage is a sensible rate (e.g., 0.00 to 0.10 for 0-10%)."]
        
        if self.stripe_fee_percentage_international is not None and not (Decimal('0.00') <= self.stripe_fee_percentage_international <= Decimal('0.10')):
            errors['stripe_fee_percentage_international'] = ["Ensure international Stripe fee percentage is a sensible rate (e.g., 0.00 to 0.10 for 0-10%)."]

        # Validate 'days' thresholds for full payments
        full_days_full_payment = self.cancellation_full_payment_full_refund_days
        partial_days_full_payment = self.cancellation_full_payment_partial_refund_days
        minimal_days_full_payment = self.cancellation_full_payment_minimal_refund_days

        if full_days_full_payment is not None and partial_days_full_payment is not None and full_days_full_payment < partial_days_full_payment:
            errors['cancellation_full_payment_full_refund_days'] = ["Full refund days must be greater than or equal to partial refund days."]
        if partial_days_full_payment is not None and minimal_days_full_payment is not None and partial_days_full_payment < minimal_days_full_payment:
            errors['cancellation_full_payment_partial_refund_days'] = ["Partial refund days must be greater than or equal to minimal refund days."]

        # Validate 'days' thresholds for deposit payments
        full_days_deposit = self.cancellation_deposit_full_refund_days
        partial_days_deposit = self.cancellation_deposit_partial_refund_days
        minimal_days_deposit = self.cancellation_deposit_minimal_refund_days

        if full_days_deposit is not None and partial_days_deposit is not None and full_days_deposit < partial_days_deposit:
            errors['cancellation_deposit_full_refund_days'] = ["Full deposit refund days must be greater than or equal to partial deposit refund days."]
        if partial_days_deposit is not None and minimal_days_deposit is not None and partial_days_deposit < minimal_days_deposit:
            errors['cancellation_deposit_partial_refund_days'] = ["Partial deposit refund days must be greater than or equal to minimal deposit refund days."]

        if errors:
            raise ValidationError(errors)


    def save(self, *args, **kwargs):
        if not self.pk and RefundPolicySettings.objects.exists():
            raise ValidationError("Only one instance of RefundPolicySettings can be created. Please edit the existing one.")
    
        self.full_clean()

        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Refund Policy Setting"
        verbose_name_plural = "Refund Policy Settings"
