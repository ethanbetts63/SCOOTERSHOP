# hire/views/utils.py

import datetime
from django.utils import timezone
from django.db.models import Q # Import Q for complex queries
from ..models import HireBooking # Import HireBooking model (assuming it's in a parent directory's models)
from inventory.models import Motorcycle # Also need Motorcycle model for type hinting/clarity
from django.contrib import messages # Import messages for the utility function
from django.shortcuts import redirect

def calculate_hire_price(motorcycle, duration_days, hire_settings):
    """
    Calculates the total hire price based on motorcycle, duration in days, and hire settings.
    """
    base_daily_rate = motorcycle.daily_hire_rate or hire_settings.default_daily_rate if hire_settings else 0
    # Add logic for weekly/monthly discounts if applicable
    total_price = base_daily_rate * duration_days
    return total_price

def calculate_hire_duration_days(pickup_date, return_date, pickup_time, return_time):
     """
     Calculates the number of hire days given separate date and time components.
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

    # Check: Is the motorcycle generally available?
    if not motorcycle.is_available:
        messages.error(request, "The selected motorcycle is currently not available.")
        return False
    
    if not temp_booking.pickup_date or not temp_booking.pickup_time or \
       not temp_booking.return_date or not temp_booking.return_time:
        messages.error(request, "Please select valid pickup and return dates/times first.")
        return redirect('hire:step2_choose_bike')

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
