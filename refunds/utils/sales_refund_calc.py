from decimal import Decimal
from datetime import datetime, time
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
            "time_since_booking_creation_hours": 0,
        }

    if booking.appointment_date:
        appointment_time = booking.appointment_time or time.min
        booking_start_datetime = timezone.make_aware(
            datetime.combine(booking.appointment_date, appointment_time)
        )
        time_difference = booking_start_datetime - cancellation_datetime
        days_until_booking = time_difference.days
    else:
        days_until_booking = -1 # Or some other logic to handle no appointment date

    total_paid = booking.amount_paid

    entitled_amount = Decimal("0.00")
    policy_applied = "N/A"

    if days_until_booking >= refund_settings.deposit_full_refund_days:
        entitled_amount = total_paid
        policy_applied = f"Full Refund ({refund_settings.deposit_full_refund_days} or more days until booking)"
    elif days_until_booking >= refund_settings.deposit_partial_refund_days:
        percentage = refund_settings.deposit_partial_refund_percentage / Decimal("100")
        entitled_amount = total_paid * percentage
        policy_applied = f"Partial Refund ({refund_settings.deposit_partial_refund_percentage}%)"
    elif days_until_booking >= refund_settings.deposit_no_refund_days:
        entitled_amount = Decimal("0.00")
        policy_applied = f"No Refund (less than {refund_settings.deposit_no_refund_days} days until booking)"
    else:
        entitled_amount = Decimal("0.00")
        policy_applied = f"No Refund (less than {refund_settings.deposit_no_refund_days} days until booking)"

    entitled_amount = max(Decimal("0.00"), min(entitled_amount, total_paid))

    return {
        "entitled_amount": entitled_amount.quantize(Decimal("0.01")),
        "details": f"Cancellation {days_until_booking} days before booking. Policy: {policy_applied}",
        "policy_applied": policy_applied,
        "days_until_booking": days_until_booking,
    }
