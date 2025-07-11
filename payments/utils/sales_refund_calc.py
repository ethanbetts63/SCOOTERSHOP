from decimal import Decimal
from datetime import datetime
from django.utils import timezone


def calculate_sales_refund_amount(
    booking, refund_policy_snapshot: dict, cancellation_datetime: datetime = None
) -> dict:
    if not cancellation_datetime:
        cancellation_datetime = timezone.now()

    if not refund_policy_snapshot:
        return {
            "entitled_amount": Decimal("0.00"),
            "details": "No refund policy snapshot available for this booking's payment.",
            "policy_applied": "N/A",
            "time_since_booking_creation_hours": "N/A",
        }

    entitled_amount = Decimal("0.00")
    policy_applied = "No Refund Policy"
    total_paid_for_calculation = booking.amount_paid or Decimal("0.00")

    # sales_enable_deposit_refund = refund_policy_snapshot.get(
    #     "sales_enable_deposit_refund", False
    # )
    # sales_enable_deposit_refund_grace_period = refund_policy_snapshot.get(
    #     "sales_enable_deposit_refund_grace_period", False
    # )
    # sales_deposit_refund_grace_period_hours = refund_policy_snapshot.get(
    #     "sales_deposit_refund_grace_period_hours", 0
    # )

    time_since_booking_creation = cancellation_datetime - booking.created_at
    time_since_booking_creation_hours = (
        time_since_booking_creation.total_seconds() / 3600
    )

    # if sales_enable_deposit_refund:
    #     if not sales_enable_deposit_refund_grace_period:
    #         entitled_amount = total_paid_for_calculation
    #         policy_applied = "Full Refund Policy (Grace Period Disabled)"
    #     elif (
    #         sales_enable_deposit_refund_grace_period
    #         and time_since_booking_creation_hours
    #         <= sales_deposit_refund_grace_period_hours
    #     ):
    #         entitled_amount = total_paid_for_calculation
    #         policy_applied = f"Full Refund Policy (Within {sales_deposit_refund_grace_period_hours} hour grace period)"
    #     else:
    #         entitled_amount = Decimal("0.00")
    # #         policy_applied = "No Refund Policy (Grace Period Expired)"
    # else:
    #     entitled_amount = Decimal("0.00")
    #     policy_applied = "No Refund Policy (Refunds Disabled)"

    entitled_amount = max(
        Decimal("0.00"), min(entitled_amount, total_paid_for_calculation)
    )

    calculation_details_str = (
        f"Cancellation occurred {time_since_booking_creation_hours:.2f} hours after booking creation. "
        f"Policy: {policy_applied}. "
        f"Calculated: {entitled_amount.quantize(Decimal('0.01'))}."
    )

    return {
        "entitled_amount": entitled_amount,
        "details": calculation_details_str,
        "policy_applied": policy_applied,
        "time_since_booking_creation_hours": time_since_booking_creation_hours,
    }
