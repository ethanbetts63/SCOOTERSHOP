# hire/views/utils.py

import datetime
from django.utils import timezone
from django.db.models import Q # Import Q for complex queries
from ..models import HireBooking # Import HireBooking model (assuming it's in a parent directory's models)
from inventory.models import Motorcycle # Also need Motorcycle model for type hinting/clarity
from django.contrib import messages # Import messages for the utility function
from django.shortcuts import redirect
from decimal import Decimal # Import Decimal for precise calculations
from math import ceil # Import ceil for rounding up hours


def calculate_hire_price(motorcycle, pickup_date, return_date, pickup_time, return_time, hire_settings):
    """
    Calculates the total hire price based on motorcycle, exact pickup/return datetimes, and hire settings.
    Uses hourly rate for bookings of 1 day or less, and daily rate for bookings greater than 1 day.
    """
    # Combine date and time into timezone-aware datetime objects
    pickup_datetime = timezone.make_aware(datetime.datetime.combine(pickup_date, pickup_time))
    return_datetime = timezone.make_aware(datetime.datetime.combine(return_date, return_time))

    duration_timedelta = return_datetime - pickup_datetime

    # If return is before or at pickup, price is 0
    if duration_timedelta.total_seconds() <= 0:
        return Decimal('0.00')

    # Re-use calculate_hire_duration_days to determine "days" for pricing tiers.
    # This function returns 1 for same-day bookings or bookings exactly 24 hours.
    # It returns > 1 for bookings spanning more than one calendar day.
    hire_duration_days_for_tiering = calculate_hire_duration_days(
        pickup_date, return_date, pickup_time, return_time
    )

    if hire_duration_days_for_tiering <= 1:
        # For bookings of 1 day or less, calculate price based on hours.
        # Calculate total hours, rounding up to the nearest full hour.
        total_hours = ceil(duration_timedelta.total_seconds() / 3600)
        
        # Ensure minimum 1 hour if duration is positive but very short (e.g., a few minutes)
        if total_hours == 0 and duration_timedelta.total_seconds() > 0:
            total_hours = 1

        # Use motorcycle's hourly rate, or fallback to hire settings' default hourly rate
        hourly_rate = motorcycle.hourly_hire_rate or hire_settings.default_hourly_rate if hire_settings else Decimal('0.00')
        
        total_price = hourly_rate * total_hours
    else:
        # For bookings longer than 1 day, use the daily rate.
        daily_rate = motorcycle.daily_hire_rate or hire_settings.default_daily_rate if hire_settings else Decimal('0.00')
        total_price = daily_rate * hire_duration_days_for_tiering

    return total_price

def calculate_hire_duration_days(pickup_date, return_date, pickup_time, return_time):
     """
     Calculates the number of hire days given separate date and time components.
     This function determines the number of 'billing days'.
     - If pickup and return are on the same day, it counts as 1 day (for hourly pricing).
     - If return time is later than pickup time on the final day, it counts as an additional day.
     """
     # Combine date and time into timezone-aware datetime objects
     pickup_datetime = timezone.make_aware(datetime.datetime.combine(pickup_date, pickup_time))
     return_datetime = timezone.make_aware(datetime.datetime.combine(return_date, return_time))

     # Handle cases where return_datetime is exactly equal to pickup_datetime or earlier, which should be 0 days
     if return_datetime <= pickup_datetime:
         return 0

     # Calculate the difference in days directly from the date components of the combined datetimes
     days = (return_datetime.date() - pickup_datetime.date()).days

     # If the duration is positive but less than a full day (i.e., days is 0 but return_datetime > pickup_datetime)
     # or if the hire spans multiple days and the return time is later than the pickup time on the final day,
     # count as 1 more day.
     if days == 0 and return_datetime > pickup_datetime:
         days = 1
     elif days > 0 and return_datetime.time() > pickup_datetime.time():
         days += 1

     return days

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
