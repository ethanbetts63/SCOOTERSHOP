from decimal import Decimal
from datetime import datetime
from django.utils import timezone
from refunds.models import RefundSettings


def calculate_sales_refund_amount(
    booking, cancellation_datetime: datetime = None
) -> dict:
    if not cancellation_datetime:
        cancellation_datetime = timezone.now()

    refund_settings = RefundSettings.objects.first()

    if not refund_settings:
        return {
            "entitled_amount": Decimal("0.00"),
            "details": "Refund settings not configured.",
            "policy_applied": "N/A",
        }
    days_since_booking = (cancellation_datetime - booking["created_at"]).days
    total_paid = booking["total_paid"]

    entitled_amount = Decimal("0.00")  # Initialize to a default value
    policy_applied = "N/A"

    if days_since_booking >= refund_settings.deposit_full_refund_days:
        entitled_amount = total_paid
        policy_applied = f"Full Refund ({refund_settings.deposit_full_refund_days} or more days since booking)"
    elif days_since_booking >= refund_settings.deposit_partial_refund_days:
        percentage = refund_settings.deposit_partial_refund_percentage / Decimal("100")
        entitled_amount = total_paid * percentage
        policy_applied = (
            f"Partial Refund ({refund_settings.deposit_partial_refund_percentage}%)"
        )
    else:  # This covers the case where days_since_booking < deposit_no_refund_days
        entitled_amount = Decimal("0.00")
        policy_applied = f"No Refund (less than {refund_settings.deposit_no_refund_days} days since booking)"

    entitled_amount = max(Decimal("0.00"), min(entitled_amount, total_paid))

    return {
        "entitled_amount": entitled_amount.quantize(Decimal("0.01")),
        "details": f"Cancellation {days_since_booking} days after booking. Policy: {policy_applied}",
        "policy_applied": policy_applied,
    }
