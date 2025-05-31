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

    print(f"DEBUG_CALC: Entering calculate_refund_amount for Booking PK: {booking.pk}")
    print(f"DEBUG_CALC: Booking payment_method (raw value): '{booking.payment_method}'")
    print(f"DEBUG_CALC: Booking payment_status: '{booking.payment_status}'")
    print(f"DEBUG_CALC: Refund policy snapshot: {refund_policy_snapshot}")


    # If no snapshot is provided or it's empty, return default no-refund
    if not refund_policy_snapshot:
        print("DEBUG_CALC: No refund policy snapshot available.")
        return {
            'entitled_amount': Decimal('0.00'),
            'details': "No refund policy snapshot available for this booking.",
            'policy_applied': 'N/A',
            'days_before_pickup': 'N/A',
        }

    # --- Early exit for specific payment methods that don't follow standard online refund policies ---
    # Payments made in-store or via unrecognized methods are not handled by this automated calculation.
    # They should result in a 0.00 calculated refund, with a note for manual processing.
    # Based on hire_booking.py, payment methods are 'online_full', 'online_deposit', 'in_store_full'.
    # Any method not 'online_full' or 'online_deposit' should be handled manually.
    if booking.payment_method not in ['online_full', 'online_deposit']:
        print(f"DEBUG_CALC: Manual refund policy triggered for payment_method: '{booking.payment_method}'")
        # Use get_payment_method_display() for the message, but handle None gracefully
        display_method = booking.get_payment_method_display() if booking.payment_method else 'None'
        return {
            'entitled_amount': Decimal('0.00'),
            'details': f"No Refund Policy: Refund for '{display_method}' payment method is handled manually.",
            'policy_applied': f"Manual Refund Policy for {display_method}",
            'days_before_pickup': 'N/A', # Not applicable for manual refunds
        }


    # Combine pickup date and time into a single datetime object
    pickup_datetime = timezone.make_aware(datetime.combine(booking.pickup_date, booking.pickup_time))
    # Calculate the time difference in full days
    time_difference = pickup_datetime - cancellation_datetime
    days_in_advance = time_difference.days # This gives full days
    print(f"DEBUG_CALC: Days in advance: {days_in_advance}")

    refund_amount = Decimal('0.00')
    policy_applied = "No Refund"
    refund_percentage = Decimal('0.00')

    # Get the total amount paid for this specific payment from the linked Payment object
    # This is the base amount for our refund calculation
    total_paid_for_calculation = booking.payment.amount if booking.payment and booking.payment.amount else Decimal('0.00') # Changed default to Decimal('0.00')
    print(f"DEBUG_CALC: Total paid for calculation: {total_paid_for_calculation}")

    # Determine which policy to apply based on the 'deposit_enabled' flag in the snapshot
    deposit_enabled = refund_policy_snapshot.get('deposit_enabled', False)
    print(f"DEBUG_CALC: Deposit enabled from snapshot: {deposit_enabled}")


    # Initialize policy variables with defaults that will be overwritten
    full_refund_days = 0
    partial_refund_days = 0
    partial_refund_percentage = Decimal('0.00')
    minimal_refund_days = 0
    minimal_refund_percentage = Decimal('0.00')
    policy_prefix = "General Policy" # Default prefix

    # Logic to select the correct policy based on snapshot settings and payment method
    # We now explicitly check for 'online_deposit' or if the booking payment status is 'deposit_paid'
    # to determine if it's a deposit. Otherwise, assume upfront.
    is_deposit_payment = False
    if deposit_enabled:
        # Check if the booking's payment status indicates a deposit was paid
        if booking.payment_status == 'deposit_paid':
            is_deposit_payment = True
            print("DEBUG_CALC: Booking payment status is 'deposit_paid'. Setting is_deposit_payment = True.")
        elif booking.payment_method == 'online_deposit': # If you have a distinct payment method for online deposits
            is_deposit_payment = True
            print("DEBUG_CALC: Booking payment method is 'online_deposit'. Setting is_deposit_payment = True.")
    print(f"DEBUG_CALC: Is deposit payment: {is_deposit_payment}")


    if is_deposit_payment:
        # Apply deposit policy
        full_refund_days = refund_policy_snapshot.get('cancellation_deposit_full_refund_days', 7)
        partial_refund_days = refund_policy_snapshot.get('cancellation_deposit_partial_refund_days', 3)
        partial_refund_percentage = Decimal(str(refund_policy_snapshot.get('cancellation_deposit_partial_refund_percentage', 50.0)))
        minimal_refund_days = refund_policy_snapshot.get('cancellation_deposit_minimal_refund_days', 1)
        minimal_refund_percentage = Decimal(str(refund_policy_snapshot.get('cancellation_deposit_minimal_refund_percentage', 0.0)))
        policy_prefix = "Deposit Payment Policy"
        print(f"DEBUG_CALC: Applying Deposit Policy. Full days: {full_refund_days}, Partial days: {partial_refund_days}, Partial %: {partial_refund_percentage}, Minimal days: {minimal_refund_days}, Minimal %: {minimal_refund_percentage}")
    else:
        # Apply upfront policy (for 'online_full' or just 'online' if it implies full payment)
        full_refund_days = refund_policy_snapshot.get('cancellation_upfront_full_refund_days', 7)
        partial_refund_days = refund_policy_snapshot.get('cancellation_upfront_partial_refund_days', 3)
        partial_refund_percentage = Decimal(str(refund_policy_snapshot.get('cancellation_upfront_partial_refund_percentage', 50.0)))
        minimal_refund_days = refund_policy_snapshot.get('cancellation_upfront_minimal_refund_days', 1)
        minimal_refund_percentage = Decimal(str(refund_policy_snapshot.get('cancellation_upfront_minimal_refund_percentage', 0.0)))
        policy_prefix = "Upfront Payment Policy"
        print(f"DEBUG_CALC: Applying Upfront Payment Policy. Full days: {full_refund_days}, Partial days: {partial_refund_days}, Partial %: {partial_refund_percentage}, Minimal days: {minimal_refund_days}, Minimal %: {minimal_refund_percentage}")


    # Perform the refund calculation based on the selected policy
    if days_in_advance >= full_refund_days:
        refund_amount = total_paid_for_calculation
        policy_applied = f"{policy_prefix}: Full Refund Policy"
        refund_percentage = Decimal('100.00')
        print(f"DEBUG_CALC: Full Refund Policy applied.")
    elif days_in_advance >= partial_refund_days:
        refund_percentage = partial_refund_percentage
        refund_amount = (total_paid_for_calculation * refund_percentage) / Decimal('100.00')
        policy_applied = f"{policy_prefix}: Partial Refund Policy ({refund_percentage}%)"
        print(f"DEBUG_CALC: Partial Refund Policy applied.")
    elif days_in_advance >= minimal_refund_days:
        refund_percentage = minimal_refund_percentage
        refund_amount = (total_paid_for_calculation * refund_percentage) / Decimal('100.00')
        policy_applied = f"{policy_prefix}: Minimal Refund Policy ({refund_percentage}%)"
        print(f"DEBUG_CALC: Minimal Refund Policy applied.")
    else:
        refund_amount = Decimal('0.00')
        policy_applied = f"{policy_prefix}: No Refund Policy (Too close to pickup or after pickup)"
        refund_percentage = Decimal('0.00')
        print(f"DEBUG_CALC: No Refund Policy applied (too close or after pickup).")

    # Ensure refund amount is not negative and not more than what was paid
    refund_amount = max(Decimal('0.00'), min(refund_amount, total_paid_for_calculation))
    print(f"DEBUG_CALC: Final refund amount (after min/max check): {refund_amount}")

    calculation_details_str = (
        f"Cancellation {days_in_advance} days before pickup. "
        f"Policy: {policy_applied}. "
        f"Calculated: {refund_amount.quantize(Decimal('0.01'))} ({refund_percentage.quantize(Decimal('0.01'))}% of {total_paid_for_calculation.quantize(Decimal('0.01'))})."
    )
    print(f"DEBUG_CALC: Calculation details string: {calculation_details_str}")

    return {
        'entitled_amount': refund_amount.quantize(Decimal('0.01')), # Round to 2 decimal places
        'details': calculation_details_str,
        'policy_applied': policy_applied,
        'days_before_pickup': days_in_advance,
    }

