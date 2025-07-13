from decimal import Decimal
from datetime import datetime
from django.utils import timezone
from refunds.models import RefundSettings

def calculate_service_refund_amount(booking, cancellation_datetime: datetime = None) -> dict:
    if not cancellation_datetime:
        cancellation_datetime = timezone.now()

    try:
        refund_settings = RefundSettings.objects.first()
    except RefundSettings.DoesNotExist:
        return {
            "entitled_amount": Decimal("0.00"),
            "details": "Refund settings not configured.",
            "policy_applied": "N/A",
        }

    dropoff_datetime = timezone.make_aware(
        datetime.combine(booking.dropoff_date, booking.dropoff_time)
    )
    time_difference = dropoff_datetime - cancellation_datetime
    days_before_dropoff = time_difference.days

    total_paid = booking.amount_paid or Decimal("0.00")
    entitled_amount = Decimal("0.00")
    policy_applied = "No Refund"

    if booking.payment_method == "online_deposit":
        if days_before_dropoff >= refund_settings.deposit_full_refund_days:
            entitled_amount = total_paid
            policy_applied = f"Full Deposit Refund ({refund_settings.deposit_full_refund_days} or more days before drop-off)"
        elif days_before_dropoff >= refund_settings.deposit_partial_refund_days:
            percentage = refund_settings.deposit_partial_refund_percentage / Decimal("100")
            entitled_amount = total_paid * percentage
            policy_applied = f"Partial Deposit Refund ({refund_settings.deposit_partial_refund_percentage}%)"
        elif days_before_dropoff >= refund_settings.deposit_no_refund_days:
            entitled_amount = Decimal("0.00")
            policy_applied = f"No Deposit Refund ({refund_settings.deposit_no_refund_days} or more days before drop-off)"
    else: # full payment
        if days_before_dropoff >= refund_settings.full_payment_full_refund_days:
            entitled_amount = total_paid
            policy_applied = f"Full Payment Refund ({refund_settings.full_payment_full_refund_days} or more days before drop-off)"
        elif days_before_dropoff >= refund_settings.full_payment_partial_refund_days:
            percentage = refund_settings.full_payment_partial_refund_percentage / Decimal("100")
            entitled_amount = total_paid * percentage
            policy_applied = f"Partial Payment Refund ({refund_settings.full_payment_partial_refund_percentage}%)"
        elif days_before_dropoff >= refund_settings.full_payment_no_refund_percentage:
            entitled_amount = Decimal("0.00")
            policy_applied = f"No Payment Refund ({refund_settings.full_payment_no_refund_percentage} or more days before drop-off)"

    entitled_amount = max(Decimal("0.00"), min(entitled_amount, total_paid))

    return {
        "entitled_amount": entitled_amount.quantize(Decimal("0.01")),
        "details": f"Cancellation {days_before_dropoff} days before drop-off. Policy: {policy_applied}",
        "policy_applied": policy_applied,
    }