# payments/hire_refund_calc.py

from decimal import Decimal
from datetime import datetime, date, timedelta
from django.utils import timezone

def calculate_refund_amount(booking, refund_policy_snapshot: dict, cancellation_datetime: datetime = None) -> dict:
    """
    Calculates the eligible refund amount for a given HireBooking based on
    the cancellation policy *snapshot* stored at the time of booking.

    Args:
        booking (HireBooking): The instance of the HireBooking model.
        refund_policy_snapshot (dict): The dictionary containing the refund policy
                                       settings captured at the time of booking.
        cancellation_datetime (datetime, optional): The exact datetime when the
            cancellation request is made. If None, timezone.now() is used.

    Returns:
        dict: A dictionary containing:
            - 'entitled_amount': The calculated refund amount (Decimal).
            - 'details': A string explaining the calculation.
            - 'policy_applied': Which policy (upfront/deposit) was used.
            - 'days_before_pickup': Number of full days before pickup.
    """
    if not cancellation_datetime:
        cancellation_datetime = timezone.now()

    # If no snapshot is provided or it's empty, return default no-refund
    if not refund_policy_snapshot:
        return {
            'entitled_amount': Decimal('0.00'),
            'details': "No refund policy snapshot available for this booking.",
            'policy_applied': 'N/A',
            'days_before_pickup': 'N/A',
        }

    # Combine pickup date and time into a single datetime object
    pickup_datetime = timezone.make_aware(datetime.combine(booking.pickup_date, booking.pickup_time))
    # Calculate the time difference in full days
    time_difference = pickup_datetime - cancellation_datetime
    days_in_advance = time_difference.days # This gives full days

    refund_amount = Decimal('0.00')
    policy_applied = "No Refund"
    refund_percentage = Decimal('0.00')

    # Get the total amount paid for this specific payment from the linked Payment object
    # This is the base amount for our refund calculation
    total_paid_for_calculation = booking.payment.amount if booking.payment and booking.payment.amount else Decimal('0.00')

    # Determine which policy to apply based on the 'deposit_enabled' flag in the snapshot
    # and the actual payment type (full vs. deposit) if deposits are enabled.
    deposit_enabled = refund_policy_snapshot.get('deposit_enabled', False)

    # Initialize policy variables with defaults that will be overwritten
    full_refund_days = 0
    partial_refund_days = 0
    partial_refund_percentage = Decimal('0.00')
    minimal_refund_days = 0
    minimal_refund_percentage = Decimal('0.00')
    policy_prefix = "General Policy" # Default prefix

    # Logic to select the correct policy based on snapshot settings
    if not deposit_enabled:
        # If deposits are NOT enabled, all payments are full payments, so apply upfront policy
        full_refund_days = refund_policy_snapshot.get('cancellation_upfront_full_refund_days', 7)
        partial_refund_days = refund_policy_snapshot.get('cancellation_upfront_partial_refund_days', 3)
        partial_refund_percentage = Decimal(str(refund_policy_snapshot.get('cancellation_upfront_partial_refund_percentage', 50.0)))
        minimal_refund_days = refund_policy_snapshot.get('cancellation_upfront_minimal_refund_days', 1)
        minimal_refund_percentage = Decimal(str(refund_policy_snapshot.get('cancellation_upfront_minimal_refund_percentage', 0.0)))
        policy_prefix = "Upfront Payment Policy"
    else:
        # If deposits ARE enabled, we need to determine if the current payment was a deposit or a full payment.
        # This requires comparing `total_paid_for_calculation` (amount from Payment model)
        # with the total booking cost and the calculated deposit amount.
        # CORRECTED: Using `booking.grand_total` as per the provided HireBooking model.
        total_booking_cost = booking.grand_total if hasattr(booking, 'grand_total') else Decimal('0.00')

        deposit_calculation_method = refund_policy_snapshot.get('default_deposit_calculation_method', 'percentage')
        expected_deposit_amount = Decimal('0.00')

        if deposit_calculation_method == 'percentage':
            deposit_percentage = Decimal(str(refund_policy_snapshot.get('deposit_percentage', 10.0)))
            expected_deposit_amount = (total_booking_cost * deposit_percentage) / Decimal('100.00')
        else: # 'fixed_amount'
            expected_deposit_amount = Decimal(str(refund_policy_snapshot.get('deposit_amount', 50.0)))

        # Determine if the payment was a full payment or a deposit payment
        # Using a small tolerance for floating point comparisons (though Decimal should minimize this)
        if abs(total_paid_for_calculation - total_booking_cost) < Decimal('0.01'):
            # This was a full payment, apply upfront policy
            full_refund_days = refund_policy_snapshot.get('cancellation_upfront_full_refund_days', 7)
            partial_refund_days = refund_policy_snapshot.get('cancellation_upfront_partial_refund_days', 3)
            partial_refund_percentage = Decimal(str(refund_policy_snapshot.get('cancellation_upfront_partial_refund_percentage', 50.0)))
            minimal_refund_days = refund_policy_snapshot.get('cancellation_upfront_minimal_refund_days', 1)
            minimal_refund_percentage = Decimal(str(refund_policy_snapshot.get('cancellation_upfront_minimal_refund_percentage', 0.0)))
            policy_prefix = "Upfront Payment Policy"
        elif abs(total_paid_for_calculation - expected_deposit_amount) < Decimal('0.01'):
            # This was a deposit payment, apply deposit policy
            full_refund_days = refund_policy_snapshot.get('cancellation_deposit_full_refund_days', 7)
            partial_refund_days = refund_policy_snapshot.get('cancellation_deposit_partial_refund_days', 3)
            partial_refund_percentage = Decimal(str(refund_policy_snapshot.get('cancellation_deposit_partial_refund_percentage', 50.0)))
            minimal_refund_days = refund_policy_snapshot.get('cancellation_deposit_minimal_refund_days', 1)
            minimal_refund_percentage = Decimal(str(refund_policy_snapshot.get('cancellation_deposit_minimal_refund_percentage', 0.0)))
            policy_prefix = "Deposit Payment Policy"
        else:
            # Payment amount does not clearly match a full payment or a deposit
            return {
                'entitled_amount': Decimal('0.00'),
                'details': "No Refund Policy: Payment amount does not match expected full or deposit payment.",
                'policy_applied': "N/A",
                'days_before_pickup': days_in_advance,
            }

    # Perform the refund calculation based on the selected policy
    if days_in_advance >= full_refund_days:
        refund_amount = total_paid_for_calculation
        policy_applied = f"{policy_prefix}: Full Refund Policy"
        refund_percentage = Decimal('100.00')
    elif days_in_advance >= partial_refund_days:
        refund_percentage = partial_refund_percentage
        refund_amount = (total_paid_for_calculation * refund_percentage) / Decimal('100.00')
        policy_applied = f"{policy_prefix}: Partial Refund Policy ({refund_percentage}%)"
    elif days_in_advance >= minimal_refund_days:
        refund_percentage = minimal_refund_percentage
        refund_amount = (total_paid_for_calculation * refund_percentage) / Decimal('100.00')
        policy_applied = f"{policy_prefix}: Minimal Refund Policy ({refund_percentage}%)"
    else:
        refund_amount = Decimal('0.00')
        policy_applied = f"{policy_prefix}: No Refund Policy (Too close to pickup or after pickup)"
        refund_percentage = Decimal('0.00')

    # Ensure refund amount is not negative and not more than what was paid
    refund_amount = max(Decimal('0.00'), min(refund_amount, total_paid_for_calculation))

    calculation_details_str = (
        f"Cancellation {days_in_advance} days before pickup. "
        f"Policy: {policy_applied}. "
        f"Calculated: {refund_amount.quantize(Decimal('0.01'))} ({refund_percentage.quantize(Decimal('0.01'))}% of {total_paid_for_calculation.quantize(Decimal('0.01'))})."
    )

    return {
        'entitled_amount': refund_amount.quantize(Decimal('0.01')), # Round to 2 decimal places
        'details': calculation_details_str,
        'policy_applied': policy_applied,
        'days_before_pickup': days_in_advance,
    }
