from decimal import Decimal
from datetime import datetime
from django.utils import timezone


def calculate_service_refund_amount(
    booking, refund_policy_snapshot, cancellation_datetime=None
):

    if not cancellation_datetime:
        cancellation_datetime = timezone.now()

    if not refund_policy_snapshot:
        return {
            "entitled_amount": Decimal("0.00"),
            "details": "No refund policy snapshot available for this booking's payment.",
            "policy_applied": "N/A",
            "days_before_dropoff": "N/A",
        }

    if booking.payment_method not in ["online_full", "online_deposit"]:
        display_method = (
            booking.get_payment_method_display() if booking.payment_method else "None"
        )
        return {
            "entitled_amount": Decimal("0.00"),
            "details": f"No Refund Policy: Refund for '{display_method}' payment method is handled manually.",
            "policy_applied": f"Manual Refund Policy for {display_method}",
            "days_before_dropoff": "N/A",
        }

    dropoff_datetime = timezone.make_aware(
        datetime.combine(booking.dropoff_date, booking.dropoff_time)
    )
    time_difference = dropoff_datetime - cancellation_datetime
    days_in_advance = time_difference.days

    refund_amount = Decimal("0.00")
    policy_applied = "No Refund"
    refund_percentage = Decimal("0.00")

    total_paid_for_calculation = (
        booking.amount_paid if booking.amount_paid else Decimal("0.00")
    )

    is_deposit_payment = False
    if (
        booking.payment_method == "online_deposit"
        or booking.payment_status == "deposit_paid"
    ):
        is_deposit_payment = True

    full_refund_days = 0
    partial_refund_days = 0
    partial_refund_percentage = Decimal("0.00")
    minimal_refund_days = 0
    minimal_refund_percentage = Decimal("0.00")
    policy_prefix = "General Policy"

    if is_deposit_payment:
        full_refund_days = refund_policy_snapshot.get(
            "cancellation_deposit_full_refund_days", 7
        )
        partial_refund_days = refund_policy_snapshot.get(
            "cancellation_deposit_partial_refund_days", 3
        )

        partial_refund_percentage = Decimal(
            str(
                refund_policy_snapshot.get(
                    "cancellation_deposit_partial_refund_percentage", 50.0
                )
            )
        )
        minimal_refund_days = refund_policy_snapshot.get(
            "cancellation_deposit_minimal_refund_days", 1
        )
        minimal_refund_percentage = Decimal(
            str(
                refund_policy_snapshot.get(
                    "cancellation_deposit_minimal_refund_percentage", 0.0
                )
            )
        )
        policy_prefix = "Deposit Payment Policy"
    else:
        full_refund_days = refund_policy_snapshot.get(
            "cancellation_full_payment_full_refund_days", 7
        )
        partial_refund_days = refund_policy_snapshot.get(
            "cancellation_full_payment_partial_refund_days", 3
        )

        partial_refund_percentage = Decimal(
            str(
                refund_policy_snapshot.get(
                    "cancellation_full_payment_partial_refund_percentage", 50.0
                )
            )
        )
        minimal_refund_days = refund_policy_snapshot.get(
            "cancellation_full_payment_minimal_refund_days", 1
        )
        minimal_refund_percentage = Decimal(
            str(
                refund_policy_snapshot.get(
                    "cancellation_full_payment_minimal_refund_percentage", 0.0
                )
            )
        )
        policy_prefix = "Full Payment Policy"

    partial_refund_percentage_calc = partial_refund_percentage / Decimal("100.00")
    minimal_refund_percentage_calc = minimal_refund_percentage / Decimal("100.00")

    if days_in_advance >= full_refund_days:
        refund_amount = total_paid_for_calculation
        policy_applied = f"{policy_prefix}: Full Refund Policy"
        refund_percentage = Decimal("100.00")
    elif days_in_advance >= partial_refund_days:
        refund_percentage = partial_refund_percentage
        refund_amount = total_paid_for_calculation * partial_refund_percentage_calc
        policy_applied = (
            f"{policy_prefix}: Partial Refund Policy ({refund_percentage}%)"
        )
    elif days_in_advance >= minimal_refund_days:
        refund_percentage = minimal_refund_percentage
        refund_amount = total_paid_for_calculation * minimal_refund_percentage_calc
        policy_applied = (
            f"{policy_prefix}: Minimal Refund Policy ({refund_percentage}%)"
        )
    else:
        refund_amount = Decimal("0.00")
        policy_applied = f"{policy_prefix}: No Refund Policy (Too close to drop-off or after drop-off)"
        refund_percentage = Decimal("0.00")

    refund_amount = max(Decimal("0.00"), min(refund_amount, total_paid_for_calculation))

    calculation_details_str = (
        f"Cancellation {days_in_advance} days before drop-off. "
        f"Policy: {policy_applied}. "
        f"Calculated: {refund_amount.quantize(Decimal('0.01'))} ({refund_percentage.quantize(Decimal('0.01'))}% of {total_paid_for_calculation.quantize(Decimal('0.01'))})."
    )

    return {
        "entitled_amount": refund_amount.quantize(Decimal("0.01")),
        "details": calculation_details_str,
        "policy_applied": policy_applied,
        "days_before_dropoff": days_in_advance,
    }
