# payments/hire_refund_calc.py

from decimal import Decimal
from datetime import datetime, date, timedelta
from django.utils import timezone

# Assuming HireSettings is in dashboard.models or hire.models
# Based on the provided file structure, it's likely in dashboard.models
from dashboard.models import HireSettings # Adjust this import if HireSettings is elsewhere

def calculate_refund_amount(hire_booking, cancellation_datetime=None):
    """
    Calculates the eligible refund amount for a given HireBooking based on
    the cancellation policy defined in HireSettings, distinguishing between
    upfront and deposit payments.

    Args:
        hire_booking (HireBooking): The instance of the HireBooking model.
        cancellation_datetime (datetime, optional): The exact datetime when the
            cancellation request is made. If None, timezone.now() is used.

    Returns:
        tuple: A tuple containing:
            - Decimal: The calculated refund amount.
            - dict: Details about how the refund was calculated (policy applied, days in advance, etc.).
    """
    if not cancellation_datetime:
        cancellation_datetime = timezone.now()

    # Ensure HireSettings exists
    try:
        hire_settings = HireSettings.objects.get(pk=1) # Assuming singleton
    except HireSettings.DoesNotExist:
        # Fallback to sensible defaults if settings are not configured
        # These defaults should reflect the new 'upfront' and 'deposit' structure
        hire_settings = type('obj', (object,), {
            'cancellation_upfront_full_refund_days': 7,
            'cancellation_upfront_partial_refund_days': 3,
            'cancellation_upfront_partial_refund_percentage': Decimal('50.00'),
            'cancellation_upfront_minimal_refund_days': 1,
            'cancellation_upfront_minimal_refund_percentage': Decimal('0.00'),
            'cancellation_deposit_full_refund_days': 7,
            'cancellation_deposit_partial_refund_days': 3,
            'cancellation_deposit_partial_refund_percentage': Decimal('50.00'),
            'cancellation_deposit_minimal_refund_days': 1,
            'cancellation_deposit_minimal_refund_percentage': Decimal('0.00'),
        })()
        # Log a warning here in a real application, e.g., logger.warning("HireSettings not found, using defaults.")


    # Combine pickup date and time into a single datetime object
    pickup_datetime = datetime.combine(hire_booking.pickup_date, hire_booking.pickup_time)

    # Calculate the time difference in full days
    time_difference = pickup_datetime - cancellation_datetime
    days_in_advance = time_difference.days # This gives full days

    refund_amount = Decimal('0.00')
    policy_applied = "No Refund"
    refund_percentage = Decimal('0.00')
    total_paid_for_calculation = Decimal('0.00') # Initialize this

    # Determine which policy to apply based on payment method
    payment_method = hire_booking.payment_method

    if payment_method == 'online_full':
        # Apply upfront cancellation policy
        total_paid_for_calculation = hire_booking.amount_paid # Use actual amount paid for full booking
        full_refund_days = hire_settings.cancellation_upfront_full_refund_days
        partial_refund_days = hire_settings.cancellation_upfront_partial_refund_days
        partial_refund_percentage = hire_settings.cancellation_upfront_partial_refund_percentage
        minimal_refund_days = hire_settings.cancellation_upfront_minimal_refund_days
        minimal_refund_percentage = hire_settings.cancellation_upfront_minimal_refund_percentage
        policy_prefix = "Upfront Payment Policy"

    elif payment_method == 'online_deposit':
        # Apply deposit cancellation policy
        total_paid_for_calculation = hire_booking.deposit_amount # Use deposit amount for calculation
        full_refund_days = hire_settings.cancellation_deposit_full_refund_days
        partial_refund_days = hire_settings.cancellation_deposit_partial_refund_days
        partial_refund_percentage = hire_settings.cancellation_deposit_partial_refund_percentage
        minimal_refund_days = hire_settings.cancellation_deposit_minimal_refund_days
        minimal_refund_percentage = hire_settings.cancellation_deposit_minimal_refund_percentage
        policy_prefix = "Deposit Payment Policy"

    elif payment_method == 'in_store_full':
        # As per instruction, no refund calculation for in-store payments.
        # It's assumed these are handled manually.
        refund_amount = Decimal('0.00')
        policy_applied = "In-Store Payment: Refund handled manually in store."
        refund_percentage = Decimal('0.00')
        total_paid_for_calculation = hire_booking.amount_paid # Still capture for details, but not used in calc

        # Return early for in-store payments as no further calculation is needed
        calculation_details = {
            'cancellation_datetime': cancellation_datetime.isoformat(),
            'pickup_datetime': pickup_datetime.isoformat(),
            'days_in_advance': days_in_advance,
            'total_paid_amount': str(total_paid_for_calculation),
            'calculated_refund_amount': str(refund_amount),
            'refund_percentage': str(refund_percentage),
            'policy_applied': policy_applied,
            'payment_method_used': payment_method,
        }
        return refund_amount, calculation_details

    else:
        # Handle cases where payment_method is None or an unexpected value
        # This could be an error or a booking not yet paid.
        refund_amount = Decimal('0.00')
        policy_applied = "No Refund Policy: Payment method not recognized or applicable."
        refund_percentage = Decimal('0.00')
        total_paid_for_calculation = hire_booking.amount_paid # Default to amount_paid for details

        # Return early for unrecognized payment methods
        calculation_details = {
            'cancellation_datetime': cancellation_datetime.isoformat(),
            'pickup_datetime': pickup_datetime.isoformat(),
            'days_in_advance': days_in_advance,
            'total_paid_amount': str(total_paid_for_calculation),
            'calculated_refund_amount': str(refund_amount),
            'refund_percentage': str(refund_percentage),
            'policy_applied': policy_applied,
            'payment_method_used': payment_method,
        }
        return refund_amount, calculation_details


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

    calculation_details = {
        'cancellation_datetime': cancellation_datetime.isoformat(),
        'pickup_datetime': pickup_datetime.isoformat(),
        'days_in_advance': days_in_advance,
        'total_paid_amount': str(total_paid_for_calculation),
        'calculated_refund_amount': str(refund_amount),
        'refund_percentage': str(refund_percentage),
        'policy_applied': policy_applied,
        'payment_method_used': payment_method,
        'full_refund_threshold_days': full_refund_days,
        'partial_refund_threshold_days': partial_refund_days,
        'partial_refund_percentage': str(partial_refund_percentage),
        'minimal_refund_threshold_days': minimal_refund_days,
        'minimal_refund_percentage': str(minimal_refund_percentage),
    }

    return refund_amount, calculation_details
