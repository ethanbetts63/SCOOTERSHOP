from django.db import models
from django.core.exceptions import ValidationError
from decimal import Decimal
import datetime


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
        effective_date = datetime.date.today().strftime("%B %d, %Y")

        return f"""
**Refund and Cancellation Policy**

*Effective Date: {effective_date}*

This Refund and Cancellation Policy ("Policy") governs the cancellation of services and the issuance of refunds for bookings made with [Your Company Name] ("the Company"). By placing a booking, you ("the Client") acknowledge and agree to the terms outlined herein.

**1. Cancellation Procedure**

1.1. To be eligible for a refund, all cancellation requests must be submitted in writing via email to [Your Contact Email] or through the client portal.
1.2. The effective date of cancellation will be the date on which the Company receives the written notification from the Client. All timeframes are calculated based on the scheduled start date and time of the booking.

**2. Policy for Bookings Made with Full Payment**

2.1. **Full Refund Eligibility:** A 100% refund of the total booking fee will be granted for cancellations received more than {self.full_payment_full_refund_days} full days prior to the scheduled service.

2.2. **Partial Refund Eligibility:** A refund of {self.full_payment_partial_refund_percentage}% of the total booking fee will be granted for cancellations received between {self.full_payment_no_refund_percentage} and {self.full_payment_full_refund_days} full days prior to the scheduled service.

2.3. **Non-Refundable Circumstances:** No refund will be issued for cancellations received less than {self.full_payment_no_refund_percentage} full days prior to the scheduled service. In such cases, the entirety of the booking fee is forfeited.

**3. Policy for Bookings Made with a Deposit**

3.1. **Full Refund of Deposit:** A 100% refund of the deposit amount will be granted for cancellations received more than {self.deposit_full_refund_days} full days prior to the scheduled service.

3.2. **Partial Refund of Deposit:** A refund of {self.deposit_partial_refund_percentage}% of the deposit amount will be granted for cancellations received between {self.deposit_no_refund_days} and {self.deposit_full_refund_days} full days prior to the scheduled service.

3.3. **Forfeiture of Deposit:** The deposit is non-refundable and will be forfeited for cancellations received less than {self.deposit_no_refund_days} full days prior to the scheduled service.

**4. Refund Processing**

4.1. Refunds will be credited to the original form of payment used at the time of booking. The Client acknowledges that processing times may vary depending on their financial institution.

**5. Policy Modifications**

5.1. The Company reserves the right to amend this Policy at its sole discretion. The most current version of the Policy will be posted on the Company's website and will be effective for all bookings made after its publication date.

---
*Please retain a copy of this policy for your records.*
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
