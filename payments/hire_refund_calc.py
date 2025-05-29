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
    the cancellation policy defined in HireSettings.

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
        hire_settings = type('obj', (object,), {
            'cancellation_upfront_full_refund_days': 7,
            'cancellation_upfront_partial_refund_days': 3,
            'cancellation_upfront_partial_refund_percentage': Decimal('50.00'),
            'cancellation_upfront_minimal_refund_days': 1,
            'cancellation_upfront_minimal_refund_percentage': Decimal('0.00'),
        })()
        # Log a warning here in a real application

    # Combine pickup date and time into a single datetime object
    pickup_datetime = datetime.combine(hire_booking.pickup_date, hire_booking.pickup_time)

    # Calculate the time difference in full days
    # We need to be careful with timezones if the application uses them heavily.
    # For simplicity, assuming both are in the same timezone or naive datetimes.
    time_difference = pickup_datetime - cancellation_datetime
    days_in_advance = time_difference.days # This gives full days

    total_paid_amount = hire_booking.amount_paid # Use amount_paid from HireBooking

    refund_amount = Decimal('0.00')
    policy_applied = "No Refund"
    refund_percentage = Decimal('0.00')

    if days_in_advance >= hire_settings.cancellation_upfront_full_refund_days:
        refund_amount = total_paid_amount
        policy_applied = "Full Refund Policy"
        refund_percentage = Decimal('100.00')
    elif days_in_advance >= hire_settings.cancellation_upfront_partial_refund_days:
        refund_percentage = hire_settings.cancellation_upfront_partial_refund_percentage
        refund_amount = (total_paid_amount * refund_percentage) / Decimal('100.00')
        policy_applied = f"Partial Refund Policy ({refund_percentage}%)"
    elif days_in_advance >= hire_settings.cancellation_upfront_minimal_refund_days:
        refund_percentage = hire_settings.cancellation_upfront_minimal_refund_percentage
        refund_amount = (total_paid_amount * refund_percentage) / Decimal('100.00')
        policy_applied = f"Minimal Refund Policy ({refund_percentage}%)"
    else:
        # If days_in_advance is less than minimal_refund_days, or negative (past pickup)
        refund_amount = Decimal('0.00')
        policy_applied = "No Refund Policy (Too close to pickup or after pickup)"
        refund_percentage = Decimal('0.00')

    # Ensure refund amount is not negative and not more than what was paid
    refund_amount = max(Decimal('0.00'), min(refund_amount, total_paid_amount))

    calculation_details = {
        'cancellation_datetime': cancellation_datetime.isoformat(),
        'pickup_datetime': pickup_datetime.isoformat(),
        'days_in_advance': days_in_advance,
        'total_paid_amount': str(total_paid_amount), # Convert Decimal to string for JSONField
        'calculated_refund_amount': str(refund_amount),
        'refund_percentage': str(refund_percentage),
        'policy_applied': policy_applied,
        'full_refund_threshold_days': hire_settings.cancellation_upfront_full_refund_days,
        'partial_refund_threshold_days': hire_settings.cancellation_upfront_partial_refund_days,
        'partial_refund_percentage': str(hire_settings.cancellation_upfront_partial_refund_percentage),
        'minimal_refund_threshold_days': hire_settings.cancellation_upfront_minimal_refund_days,
        'minimal_refund_percentage': str(hire_settings.cancellation_upfront_minimal_refund_percentage),
    }

    return refund_amount, calculation_details

