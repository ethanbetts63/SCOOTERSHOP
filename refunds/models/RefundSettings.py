from django.db import models
from django.core.exceptions import ValidationError
from decimal import Decimal


class RefundSettings(models.Model):

    full_payment_full_refund_days = models.PositiveIntegerField(
        default=7,
        help_text="Full refund if cancelled this many *full days* or more before the booking's start time (for full payments).",
    )
    full_payment_partial_refund_days = models.PositiveIntegerField(
        default=3,
        help_text="Partial refund if cancelled this many *full days* or more (but less than full refund threshold) before the booking's start time (for full payments).",
    )
    full_payment_partial_refund_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=50.00,
        help_text="Percentage of total booking price to refund for partial cancellations (for full payments).",
    )
    full_payment_no_refund_percentage = models.PositiveIntegerField(
        default=1,
        help_text="Minimal refund percentage applies if cancelled this many *full days* or more (but less than partial refund threshold) before the booking's start time (for full payments).",
    )

    deposit_full_refund_days = models.PositiveIntegerField(
        default=7,
        help_text="Full refund of deposit if cancelled this many *full days* or more before the booking's start time.",
    )
    deposit_partial_refund_days = models.PositiveIntegerField(
        default=3,
        help_text="Partial refund of deposit if cancelled this many *full days* or more (but less than full refund threshold) before the booking's start time.",
    )
    deposit_partial_refund_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=50.00,
        help_text="Percentage of deposit to refund for partial cancellations.",
    )
    deposit_no_refund_days = models.PositiveIntegerField(
        default=1,
        help_text="Minimal refund percentage applies to deposit if cancelled this many *full days* or more (but less than partial refund threshold) before the booking's start time.",
    )


    def generate_policy_text(self):
        return f"""
# Refund Policy

## Full Payments

### Full Refund
- **Eligibility:** Cancellations made more than {self.full_payment_full_refund_days} days before the scheduled service or pickup date.
- **Process:** The full payment amount will be refunded to the original payment method.

### Partial Refund
- **Eligibility:** Cancellations made between {self.full_payment_no_refund_percentage} and {self.full_payment_full_refund_days} days before the scheduled date.
- **Refund Amount:** {self.full_payment_partial_refund_percentage}% of the total payment will be refunded.
- **Process:** The partial refund will be processed to the original payment method.

### No Refund
- **Eligibility:** Cancellations made less than {self.full_payment_no_refund_percentage} days before the scheduled date.
- **Outcome:** The payment is non-refundable.

## Deposits

### Full Refund
- **Eligibility:** Cancellations made more than {self.deposit_full_refund_days} days before the scheduled service or pickup date.
- **Process:** The full deposit amount will be refunded to the original payment method.

### Partial Refund
- **Eligibility:** Cancellations made between {self.deposit_no_refund_days} and {self.deposit_full_refund_days} days before the scheduled date.
- **Refund Amount:** {self.deposit_partial_refund_percentage}% of the deposit will be refunded.
- **Process:** The partial refund will be processed to the original payment method.

### No Refund
- **Eligibility:** Cancellations made less than {self.deposit_no_refund_days} days before the scheduled date.
- **Outcome:** The deposit is non-refundable.
"""

    def __str__(self):
        return "Refund Policy Settings"

    def clean(self):
        errors = {}

        percentage_fields = [
            "full_payment_partial_refund_percentage",
            "deposit_partial_refund_percentage",
        ]
        for field_name in percentage_fields:
            value = getattr(self, field_name)
            if value is not None and not (
                Decimal("0.00") <= value <= Decimal("100.00")
            ):
                errors[field_name] = [
                    f"Ensure {field_name.replace('_', ' ')} is between 0.00% and 100.00%."
                ]


        full_days_full_payment = self.full_payment_full_refund_days
        partial_days_full_payment = self.full_payment_partial_refund_days
        minimal_days_full_payment = self.full_payment_no_refund_percentage

        if (
            full_days_full_payment is not None
            and partial_days_full_payment is not None
            and full_days_full_payment < partial_days_full_payment
        ):
            errors["full_payment_full_refund_days"] = [
                "Full refund days must be greater than or equal to partial refund days."
            ]
        if (
            partial_days_full_payment is not None
            and minimal_days_full_payment is not None
            and partial_days_full_payment < minimal_days_full_payment
        ):
            errors["full_payment_partial_refund_days"] = [
                "Partial refund days must be greater than or equal to minimal refund days."
            ]

        full_days_deposit = self.deposit_full_refund_days
        partial_days_deposit = self.deposit_partial_refund_days
        minimal_days_deposit = self.deposit_no_refund_days

        if (
            full_days_deposit is not None
            and partial_days_deposit is not None
            and full_days_deposit < partial_days_deposit
        ):
            errors["deposit_full_refund_days"] = [
                "Full deposit refund days must be greater than or equal to partial deposit refund days."
            ]
        if (
            partial_days_deposit is not None
            and minimal_days_deposit is not None
            and partial_days_deposit < minimal_days_deposit
        ):
            errors["deposit_partial_refund_days"] = [
                "Partial deposit refund days must be greater than or equal to minimal deposit refund days."
            ]

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if not self.pk and RefundSettings.objects.exists():
            raise ValidationError(
                "Only one instance of RefundSettings can be created. Please edit the existing one."
            )

        self.full_clean()

        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Refund Policy Setting"
        verbose_name_plural = "Refund Policy Settings"
