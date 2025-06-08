# payments/utils/service_refund_calc.py

from decimal import Decimal
from datetime import datetime, date, timedelta
from django.utils import timezone
# Import the ServiceBooking model instead of HireBooking
from service.models import ServiceBooking

def calculate_refund_amount(booking, refund_policy_snapshot, cancellation_datetime=None):
    """
    Calculates the eligible refund amount for a given ServiceBooking based on
    the cancellation policy *snapshot* stored at the time of booking's payment.

    Args:
        booking: The instance of the ServiceBooking model.
        refund_policy_snapshot (dict): The dictionary containing the refund policy
                                       settings captured at the time of booking's payment.
        cancellation_datetime (datetime, optional): The exact datetime when the
            cancellation request is made. If None, timezone.now() is used.

    Returns:
        dict: A dictionary containing:
            - 'entitled_amount': The calculated refund amount (Decimal).
            - 'details': A string explaining the calculation.
            - 'policy_applied': Which policy (full_payment/deposit) was used.
            - 'days_before_dropoff': Number of full days before the service drop-off date.
    """
    if not cancellation_datetime:
        cancellation_datetime = timezone.now()

    if not refund_policy_snapshot:
        return {
            'entitled_amount': Decimal('0.00'),
            'details': "No refund policy snapshot available for this booking's payment.",
            'policy_applied': 'N/A',
            'days_before_dropoff': 'N/A',
        }

    # If payment method is not online, assume manual refund handling
    if booking.payment_method not in ['online_full', 'online_deposit']:
        display_method = booking.get_payment_method_display() if booking.payment_method else 'None'
        return {
            'entitled_amount': Decimal('0.00'),
            'details': f"No Refund Policy: Refund for '{display_method}' payment method is handled manually.",
            'policy_applied': f"Manual Refund Policy for {display_method}",
            'days_before_dropoff': 'N/A',
        }

    # For ServiceBooking, the relevant start time for refund calculation is typically drop-off
    dropoff_datetime = timezone.make_aware(datetime.combine(booking.dropoff_date, booking.dropoff_time))
    time_difference = dropoff_datetime - cancellation_datetime
    days_in_advance = time_difference.days

    refund_amount = Decimal('0.00')
    policy_applied = "No Refund"
    refund_percentage = Decimal('0.00')

    # 'amount_paid' is on ServiceBooking itself, but 'payment.amount' is also valid for total payment.
    # We use booking.amount_paid as it represents what the customer actually paid for the booking.
    total_paid_for_calculation = booking.amount_paid if booking.amount_paid else Decimal('0.00')

    # The actual payment method used for the booking determines if it's a deposit payment
    is_deposit_payment = False
    if booking.payment_method == 'online_deposit' or booking.payment_status == 'deposit_paid':
        is_deposit_payment = True

    full_refund_days = 0
    partial_refund_days = 0
    partial_refund_percentage = Decimal('0.00')
    minimal_refund_days = 0
    minimal_refund_percentage = Decimal('0.00')
    policy_prefix = "General Policy"

    if is_deposit_payment:
        full_refund_days = refund_policy_snapshot.get('cancellation_deposit_full_refund_days', 7)
        partial_refund_days = refund_policy_snapshot.get('cancellation_deposit_partial_refund_days', 3)
        # Convert percentage from X.00 format (e.g., 50.00) to 0.XX (e.g., 0.50) for calculation
        partial_refund_percentage = Decimal(str(refund_policy_snapshot.get('cancellation_deposit_partial_refund_percentage', 50.0)))
        minimal_refund_days = refund_policy_snapshot.get('cancellation_deposit_minimal_refund_days', 1)
        minimal_refund_percentage = Decimal(str(refund_policy_snapshot.get('cancellation_deposit_minimal_refund_percentage', 0.0)))
        policy_prefix = "Deposit Payment Policy"
    else: # Assumes full payment if not deposit payment
        full_refund_days = refund_policy_snapshot.get('cancellation_full_payment_full_refund_days', 7)
        partial_refund_days = refund_policy_snapshot.get('cancellation_full_payment_partial_refund_days', 3)
        # Convert percentage from X.00 format (e.g., 50.00) to 0.XX (e.g., 0.50) for calculation
        partial_refund_percentage = Decimal(str(refund_policy_snapshot.get('cancellation_full_payment_partial_refund_percentage', 50.0)))
        minimal_refund_days = refund_policy_snapshot.get('cancellation_full_payment_minimal_refund_days', 1)
        minimal_refund_percentage = Decimal(str(refund_policy_snapshot.get('cancellation_full_payment_minimal_refund_percentage', 0.0)))
        policy_prefix = "Full Payment Policy"

    # Convert percentage values from X.00 format (e.g., 50.00) to 0.XX for calculation
    # This ensures consistency since our RefundPolicySettings now store them as 50.00, not 0.50
    partial_refund_percentage_calc = partial_refund_percentage / Decimal('100.00')
    minimal_refund_percentage_calc = minimal_refund_percentage / Decimal('100.00')

    if days_in_advance >= full_refund_days:
        refund_amount = total_paid_for_calculation
        policy_applied = f"{policy_prefix}: Full Refund Policy"
        refund_percentage = Decimal('100.00')
    elif days_in_advance >= partial_refund_days:
        refund_percentage = partial_refund_percentage # Keep original value for display
        refund_amount = (total_paid_for_calculation * partial_refund_percentage_calc) # Use calculated percentage
        policy_applied = f"{policy_prefix}: Partial Refund Policy ({refund_percentage}%)"
    elif days_in_advance >= minimal_refund_days:
        refund_percentage = minimal_refund_percentage # Keep original value for display
        refund_amount = (total_paid_for_calculation * minimal_refund_percentage_calc) # Use calculated percentage
        policy_applied = f"{policy_prefix}: Minimal Refund Policy ({refund_percentage}%)"
    else:
        refund_amount = Decimal('0.00')
        policy_applied = f"{policy_prefix}: No Refund Policy (Too close to drop-off or after drop-off)"
        refund_percentage = Decimal('0.00')

    refund_amount = max(Decimal('0.00'), min(refund_amount, total_paid_for_calculation))

    calculation_details_str = (
        f"Cancellation {days_in_advance} days before drop-off. "
        f"Policy: {policy_applied}. "
        f"Calculated: {refund_amount.quantize(Decimal('0.01'))} ({refund_percentage.quantize(Decimal('0.01'))}% of {total_paid_for_calculation.quantize(Decimal('0.01'))})."
    )

    return {
        'entitled_amount': refund_amount.quantize(Decimal('0.01')),
        'details': calculation_details_str,
        'policy_applied': policy_applied,
        'days_before_dropoff': days_in_advance,
    }
