# hire/views/utils.py

import datetime
from django.utils import timezone
from django.db.models import Q # Import Q for complex queries
from ..models import HireBooking # Import HireBooking model (assuming it's in a parent directory's models)
from inventory.models import Motorcycle # Also need Motorcycle model for type hinting/clarity
from django.contrib import messages # Import messages for the utility function
from django.shortcuts import redirect
from decimal import Decimal # Import Decimal for precise calculations
import datetime
from decimal import Decimal, ROUND_HALF_UP
from math import ceil, floor # Import these for rounding operations

# Import models
from dashboard.models import HireSettings

def calculate_hire_price(motorcycle, pickup_date, return_date, pickup_time, return_time, hire_settings):
    """
    Calculates the total hire price based on the selected motorcycle, dates, times,
    and the configured hire pricing strategy in HireSettings.
    """
    # Combine date and time into datetime objects
    pickup_datetime = datetime.datetime.combine(pickup_date, pickup_time)
    return_datetime = datetime.datetime.combine(return_date, return_time)

    # Ensure return_datetime is after pickup_datetime
    if return_datetime <= pickup_datetime:
        return Decimal('0.00')

    # Get rates, prioritizing motorcycle-specific rates over default settings
    daily_rate = motorcycle.daily_hire_rate if motorcycle.daily_hire_rate is not None else hire_settings.default_daily_rate
    hourly_rate = motorcycle.hourly_hire_rate if motorcycle.hourly_hire_rate is not None else hire_settings.default_hourly_rate

    # Handle cases where rates are not set (should ideally be prevented by HireSettings defaults)
    if daily_rate is None or hourly_rate is None:
        print("WARNING: Daily or hourly rate not set for motorcycle or default settings. Returning 0.00.")
        return Decimal('0.00')

    # Get the chosen pricing strategy
    pricing_strategy = hire_settings.hire_pricing_strategy

    # Calculate total duration in hours (as a Decimal for precision)
    total_duration_seconds = (return_datetime - pickup_datetime).total_seconds()
    # Quantize to 2 decimal places for consistency, but keep it as Decimal
    total_duration_hours = Decimal(total_duration_seconds / 3600).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)

    # Handle same-day hire (always hourly, rounded up to nearest hour)
    # This logic applies *before* multi-day strategies
    if pickup_date == return_date:
        # If duration is less than 1 hour but positive, still charge for 1 hour
        # Use Decimal for calculations to maintain precision
        billed_hours = max(Decimal('1.00'), total_duration_hours.quantize(Decimal('1.'), rounding=ROUND_HALF_UP))
        return billed_hours * hourly_rate

    # Dispatch to the appropriate pricing strategy function for multi-day hires
    if pricing_strategy == 'flat_24_hour':
        return _calculate_flat_24_hour_billing(total_duration_hours, daily_rate)
    elif pricing_strategy == '24_hour_plus_margin':
        return _calculate_24_hour_plus_margin_billing(total_duration_hours, daily_rate, hourly_rate, hire_settings.excess_hours_margin)
    elif pricing_strategy == '24_hour_customer_friendly':
        return _calculate_24_hour_customer_friendly_billing(total_duration_hours, daily_rate, hourly_rate)
    elif pricing_strategy == 'daily_plus_excess_hourly':
        return _calculate_daily_plus_excess_hourly_billing(total_duration_hours, daily_rate, hourly_rate)
    else:
        # Fallback or error for unknown strategy
        print(f"ERROR: Unknown hire pricing strategy: {pricing_strategy}. Returning 0.00.")
        return Decimal('0.00')


def _calculate_flat_24_hour_billing(total_duration_hours, daily_rate):
    """
    Strategy 1: Flat 24-hour billing cycle. If they go past the pickup time, it's an extra day.
    Any partial hour pushes it to the next full day.
    """
    # Convert total_duration_hours to days, rounding up any fraction of a day.
    # Use float for ceil, then convert back to Decimal for multiplication.
    billed_days = Decimal(ceil(float(total_duration_hours) / 24)).quantize(Decimal('1.'), rounding=ROUND_HALF_UP)
    return billed_days * daily_rate


def _calculate_24_hour_plus_margin_billing(total_duration_hours, daily_rate, hourly_rate, excess_hours_margin):
    """
    Strategy 2: 24-hour billing cycle plus margin. If they go past the pickup time
    on the final day, they have x number of hours margin before being charged for a full day.
    """
    full_24_hour_blocks = Decimal(floor(float(total_duration_hours) / 24)).quantize(Decimal('1.'), rounding=ROUND_HALF_UP)
    remaining_excess_hours = total_duration_hours % 24

    additional_charge = Decimal('0.00')
    # Check if there are any remaining hours and if they exceed the margin
    if remaining_excess_hours > Decimal('0.00') and remaining_excess_hours > Decimal(excess_hours_margin):
        # If excess hours exceed the margin, charge for a full extra day
        additional_charge = daily_rate
    # If remaining_excess_hours is 0 or within the margin, no additional charge for excess time.

    return (full_24_hour_blocks * daily_rate) + additional_charge


def _calculate_24_hour_customer_friendly_billing(total_duration_hours, daily_rate, hourly_rate):
    """
    Strategy 3: 24-hour billing customer friendly. If they go past the pickup time
    on the final day, they are charged the hourly price or day price whichever is less.
    """
    full_24_hour_blocks = Decimal(floor(float(total_duration_hours) / 24)).quantize(Decimal('1.'), rounding=ROUND_HALF_UP)
    remaining_excess_hours = total_duration_hours % 24

    additional_cost = Decimal('0.00')
    if remaining_excess_hours > Decimal('0.00'):
        # Round up remaining excess hours to the nearest full hour for hourly billing
        # Use float for ceil, then convert back to Decimal
        billed_excess_hours = Decimal(ceil(float(remaining_excess_hours))).quantize(Decimal('1.'), rounding=ROUND_HALF_UP)
        cost_by_hourly_rate = billed_excess_hours * hourly_rate
        additional_cost = min(cost_by_hourly_rate, daily_rate) # Take the cheaper of hourly vs. full day

    return (full_24_hour_blocks * daily_rate) + additional_cost


def _calculate_daily_plus_excess_hourly_billing(total_duration_hours, daily_rate, hourly_rate):
    """
    Strategy 4: Daily plus excess hourly. Every additional hour after the pick up time
    on the final day is charged at an hourly rate.
    """
    full_24_hour_blocks = Decimal(floor(float(total_duration_hours) / 24)).quantize(Decimal('1.'), rounding=ROUND_HALF_UP)
    remaining_excess_hours = total_duration_hours % 24

    additional_cost = Decimal('0.00')
    if remaining_excess_hours > Decimal('0.00'):
        # Round up remaining excess hours to the nearest full hour for hourly billing
        # Use float for ceil, then convert back to Decimal
        billed_excess_hours = Decimal(ceil(float(remaining_excess_hours))).quantize(Decimal('1.'), rounding=ROUND_HALF_UP)
        additional_cost = billed_excess_hours * hourly_rate

    return (full_24_hour_blocks * daily_rate) + additional_cost


def calculate_hire_duration_days(motorcycle, pickup_date, return_date, pickup_time, return_time, hire_settings):
    """
    Calculates the *billable* duration in days based on the selected pricing strategy.
    This function now also needs access to hire_settings and motorcycle for rates.
    """
    # Combine date and time into datetime objects
    pickup_datetime = datetime.datetime.combine(pickup_date, pickup_time)
    return_datetime = datetime.datetime.combine(return_date, return_time)

    if return_datetime <= pickup_datetime:
        return 0

    # Get the chosen pricing strategy
    pricing_strategy = hire_settings.hire_pricing_strategy

    total_duration_seconds = (return_datetime - pickup_datetime).total_seconds()
    total_duration_hours = Decimal(total_duration_seconds / 3600).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)

    # Get rates, prioritizing motorcycle-specific rates over default settings
    daily_rate = motorcycle.daily_hire_rate if motorcycle.daily_hire_rate is not None else hire_settings.default_daily_rate
    hourly_rate = motorcycle.hourly_hire_rate if motorcycle.hourly_hire_rate is not None else hire_settings.default_hourly_rate


    # Handle same-day hire: Always 1 billable day for display if positive duration
    if pickup_date == return_date:
        return 1 if total_duration_hours > 0 else 0

    # Dispatch to the appropriate logic for multi-day hires to determine billable days
    # if pricing_strategy == 'flat_24_hour':
    #     # Any partial hour pushes it to the next full day.
    #     return int(ceil(float(total_duration_hours) / 24))
    if pricing_strategy == 'flat_24_hour':
        total_hours = total_seconds / 3600
        return int(ceil(total_hours / 24))
    elif pricing_strategy == 'flat_24_hour':
        pickup_datetime = datetime.datetime.combine(pickup_date, pickup_time)
        return_datetime = datetime.datetime.combine(return_date, return_time)
        duration = return_datetime - pickup_datetime
        total_seconds = duration.total_seconds()
        if total_seconds <= 0:
            return 0
    elif pricing_strategy == '24_hour_plus_margin':
        full_24_hour_blocks = floor(float(total_duration_hours) / 24)
        remaining_excess_hours = total_duration_hours % 24
        if remaining_excess_hours > Decimal('0.00') and remaining_excess_hours > Decimal(hire_settings.excess_hours_margin):
            return int(full_24_hour_blocks + 1) # Charge for an extra day
        else:
            return int(full_24_hour_blocks) # Only full days are billed (or 0 if less than 24h total)
    elif pricing_strategy == '24_hour_customer_friendly':
        full_24_hour_blocks = floor(float(total_duration_hours) / 24)
        remaining_excess_hours = total_duration_hours % 24
        if remaining_excess_hours > Decimal('0.00'):
            billed_excess_hours = Decimal(ceil(float(remaining_excess_hours))).quantize(Decimal('1.'), rounding=ROUND_HALF_UP)
            cost_by_hourly_rate = billed_excess_hours * hourly_rate
            # If the hourly cost of excess is cheaper than a full day, it's still part of the *last* day.
            # If it's equal to or more than a daily rate, it's an additional day.
            if cost_by_hourly_rate >= daily_rate:
                return int(full_24_hour_blocks + 1)
            else:
                # If hourly cost is less than a day, it's still considered part of the last day.
                # If there are no full 24-hour blocks but there are excess hours, it's 1 day for display.
                return int(max(1, full_24_hour_blocks)) if full_24_hour_blocks == 0 else int(full_24_hour_blocks)
        else:
            return int(full_24_hour_blocks)
    elif pricing_strategy == 'daily_plus_excess_hourly':
        # This strategy charges hourly for excess, so the 'days' count is just full 24-hour blocks.
        return int(floor(float(total_duration_hours) / 24))
    else:
        # Fallback for unknown strategy, perhaps default to 0 or raise an error
        return 0 # Or raise an error as this indicates an invalid configuration


def get_overlapping_motorcycle_bookings(motorcycle, pickup_date, pickup_time, return_date, return_time, exclude_booking_id=None):
    """
    Checks for existing HireBookings that overlap with the given date/time range for a specific motorcycle.
    """
    # Combine date and time into timezone-aware datetime objects
    pickup_datetime = timezone.make_aware(datetime.datetime.combine(pickup_date, pickup_time))
    return_datetime = timezone.make_aware(datetime.datetime.combine(return_date, return_time))

    # Ensure return_datetime is after pickup_datetime for a valid range
    # This check is now also performed in is_motorcycle_available, but kept here for robustness
    if return_datetime <= pickup_datetime:
        return []

    # Find bookings for the specified motorcycle that are not cancelled, completed, or no_show
    # and whose date ranges potentially overlap.
    potential_overlaps = HireBooking.objects.filter(
        motorcycle=motorcycle,
        # Corrected: Removed .date() as pickup_date and return_date are already date objects
        pickup_date__lt=return_datetime.date(),
        return_date__gt=pickup_date
    ).exclude(
        status__in=['cancelled', 'completed', 'no_show']
    )

    # Exclude a specific booking if provided (e.g., when editing an existing booking)
    if exclude_booking_id:
        potential_overlaps = potential_overlaps.exclude(id=exclude_booking_id)

    actual_overlaps = []
    for booking in potential_overlaps:
        booking_pickup_dt = timezone.make_aware(datetime.datetime.combine(booking.pickup_date, booking.pickup_time))
        booking_return_dt = timezone.make_aware(datetime.datetime.combine(booking.return_date, booking.return_time))

        # Perform precise datetime overlap check:
        # The intervals [start1, end1) and [start2, end2) overlap if max(start1, start2) < min(end1, end2)
        if max(pickup_datetime, booking_pickup_dt) < min(return_datetime, booking_return_dt):
            actual_overlaps.append(booking)

    return actual_overlaps

def is_motorcycle_available(request, motorcycle, temp_booking):
    """
    Checks if a motorcycle is available for the given temporary booking dates and license type.
    Adds messages and returns False if not available.
    """
    # Check: Is the motorcycle generally available?
    if not motorcycle.is_available:
        messages.error(request, "The selected motorcycle is currently not available.")
        return False

    # Check for basic date/time validity first
    if not temp_booking.pickup_date or not temp_booking.pickup_time or \
       not temp_booking.return_date or not temp_booking.return_time:
        messages.error(request, "Please select valid pickup and return dates/times first.")
        return False

    # Combine into datetime objects for comparison
    pickup_datetime = timezone.make_aware(datetime.datetime.combine(temp_booking.pickup_date, temp_booking.pickup_time))
    return_datetime = timezone.make_aware(datetime.datetime.combine(temp_booking.return_date, temp_booking.return_time))

    # Explicitly check if return date/time is before or same as pickup date/time
    if return_datetime <= pickup_datetime:
        messages.error(request, "Return time must be after pickup time.")
        return False

    # Check for license compatibility
    if motorcycle.engine_size > 50 and not temp_booking.has_motorcycle_license:
        messages.error(request, "You require a full motorcycle license for this motorcycle.")
        return False

    # Check: Are there any conflicting permanent bookings?
    conflicting_bookings = get_overlapping_motorcycle_bookings(
        motorcycle,
        temp_booking.pickup_date,
        temp_booking.pickup_time,
        temp_booking.return_date,
        temp_booking.return_time
    )
    if conflicting_bookings:
        messages.error(request, "The selected motorcycle is not available for your chosen dates/times due to an existing booking.")
        return False

    return True
