
# hire/views/utils.py

import datetime
from django.utils import timezone
from ..models import HireBooking
from inventory.models import Motorcycle
from django.contrib import messages
from decimal import Decimal, ROUND_HALF_UP
from math import ceil, floor
from dashboard.models import HireSettings

def calculate_hire_duration_days(motorcycle, pickup_date, return_date, pickup_time, return_time, hire_settings):
    pickup_datetime = datetime.datetime.combine(pickup_date, pickup_time)
    return_datetime = datetime.datetime.combine(return_date, return_time)

    if return_datetime <= pickup_datetime:
        return 0

    pricing_strategy = hire_settings.hire_pricing_strategy 
    total_duration_seconds = (return_datetime - pickup_datetime).total_seconds()
    total_hours_float = total_duration_seconds / 3600.0

    daily_rate = motorcycle.daily_hire_rate if motorcycle.daily_hire_rate is not None else hire_settings.default_daily_rate
    hourly_rate = motorcycle.hourly_hire_rate if motorcycle.hourly_hire_rate is not None else hire_settings.default_hourly_rate

    # For same-day hires, it counts as 1 day if there's any duration.
    if pickup_date == return_date:
        return 1 if total_hours_float > 0 else 0

    # For multi-day hires, calculates billed days based on the specific pricing strategy.
    if pricing_strategy == 'flat_24_hour':
        return int(ceil(total_hours_float / 24.0))
    elif pricing_strategy == '24_hour_plus_margin':
        full_24_hour_blocks = floor(total_hours_float / 24.0)
        remaining_excess_hours_float = total_hours_float % 24.0
        margin_hours_float = float(hire_settings.excess_hours_margin) 
        if remaining_excess_hours_float > 0.0 and remaining_excess_hours_float > margin_hours_float:
            return int(full_24_hour_blocks + 1)
        else:
            return int(full_24_hour_blocks) if full_24_hour_blocks > 0 else (1 if total_hours_float > 0 else 0)
    elif pricing_strategy == '24_hour_customer_friendly':
        if daily_rate is None or hourly_rate is None: return 0 
        full_24_hour_blocks = floor(total_hours_float / 24.0)
        remaining_excess_hours_float = total_hours_float % 24.0
        if remaining_excess_hours_float > 0.0:
            billed_excess_hours_for_cost_check = ceil(remaining_excess_hours_float)
            cost_by_hourly_rate_for_check = Decimal(billed_excess_hours_for_cost_check) * hourly_rate
            if cost_by_hourly_rate_for_check >= daily_rate: 
                return int(full_24_hour_blocks + 1)
            else: 
                if full_24_hour_blocks > 0:
                    return int(full_24_hour_blocks + (1 if remaining_excess_hours_float > 0 else 0))
                else: 
                    return 1 if total_hours_float > 0 else 0
        else: 
            return int(full_24_hour_blocks) if full_24_hour_blocks > 0 else (1 if total_hours_float > 0 else 0)
    elif pricing_strategy == 'daily_plus_excess_hourly':
        num_days = floor(total_hours_float / 24.0)
        if total_hours_float % 24.0 > 0:
            num_days +=1
        return int(max(1,num_days) if total_hours_float > 0 else 0) 
    else:
        return 0 

def get_overlapping_motorcycle_bookings(motorcycle, pickup_date, pickup_time, return_date, return_time, exclude_booking_id=None):
    # Retrieves existing hire bookings for a motorcycle that conflict with the given period.
    pickup_datetime = timezone.make_aware(datetime.datetime.combine(pickup_date, pickup_time))
    return_datetime = timezone.make_aware(datetime.datetime.combine(return_date, return_time))

    if return_datetime <= pickup_datetime:
        return []

    potential_overlaps = HireBooking.objects.filter(
        motorcycle=motorcycle,
        pickup_date__lt=return_datetime.date(), 
        return_date__gt=pickup_datetime.date()  
    ).exclude(
        status__in=['cancelled', 'completed', 'no_show'] 
    )

    if exclude_booking_id:
        potential_overlaps = potential_overlaps.exclude(id=exclude_booking_id)

    actual_overlaps = []
    for booking in potential_overlaps:
        if booking.pickup_time is None or booking.return_time is None:
            continue

        booking_pickup_dt = timezone.make_aware(datetime.datetime.combine(booking.pickup_date, booking.pickup_time))
        booking_return_dt = timezone.make_aware(datetime.datetime.combine(booking.return_date, booking.return_time))
        
        if pickup_datetime < booking_return_dt and booking_pickup_dt < return_datetime:
            actual_overlaps.append(booking)
    return actual_overlaps

def is_motorcycle_available(request, motorcycle, temp_booking):
    # Checks if the motorcycle is generally available.
    if not motorcycle.is_available: 
        messages.error(request, "The selected motorcycle is currently not available.")
        return False

    # Validates that pickup and return dates/times are selected.
    if not temp_booking.pickup_date or not temp_booking.pickup_time or \
       not temp_booking.return_date or not temp_booking.return_time: 
        messages.error(request, "Please select valid pickup and return dates/times first.")
        return False

    # Ensures return time is after pickup time.
    if datetime.datetime.combine(temp_booking.return_date, temp_booking.return_time) <= \
       datetime.datetime.combine(temp_booking.pickup_date, temp_booking.pickup_time):
        messages.error(request, "Return time must be after pickup time.")
        return False

    # Checks for motorcycle license requirement based on engine size.
    if motorcycle.engine_size > 50 and not temp_booking.has_motorcycle_license:
        messages.error(request, "You require a full motorcycle license for this motorcycle.")
        return False

    # Checks for overlapping bookings to ensure availability.
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