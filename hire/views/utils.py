# hire/views/utils.py

import datetime
from django.utils import timezone
from ..models import HireBooking
from inventory.models import Motorcycle
from django.contrib import messages
from decimal import Decimal, ROUND_HALF_UP
from math import ceil, floor
from dashboard.models import HireSettings

# Calculates the total hire price based on strategy and motorcycle/default rates.
def calculate_hire_price(motorcycle, pickup_date, return_date, pickup_time, return_time, hire_settings):
    pickup_datetime = datetime.datetime.combine(pickup_date, pickup_time)
    return_datetime = datetime.datetime.combine(return_date, return_time)

    if return_datetime <= pickup_datetime:
        return Decimal('0.00')

    daily_rate = motorcycle.daily_hire_rate if motorcycle.daily_hire_rate is not None else hire_settings.default_daily_rate
    hourly_rate = motorcycle.hourly_hire_rate if motorcycle.hourly_hire_rate is not None else hire_settings.default_hourly_rate

    if daily_rate is None or hourly_rate is None:
        return Decimal('0.00')

    pricing_strategy = hire_settings.hire_pricing_strategy
    total_duration_seconds = (return_datetime - pickup_datetime).total_seconds()
    total_duration_hours = Decimal(total_duration_seconds / 3600).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)

    # Same-day hires are always billed hourly, rounded up.
    if pickup_date == return_date:
        billed_hours = max(Decimal('1.00'), total_duration_hours.quantize(Decimal('1.'), rounding=ROUND_HALF_UP))
        return billed_hours * hourly_rate

    if pricing_strategy == 'flat_24_hour':
        return _calculate_flat_24_hour_billing(total_duration_hours, daily_rate)
    elif pricing_strategy == '24_hour_plus_margin':
        return _calculate_24_hour_plus_margin_billing(total_duration_hours, daily_rate, hourly_rate, hire_settings.excess_hours_margin)
    elif pricing_strategy == '24_hour_customer_friendly':
        return _calculate_24_hour_customer_friendly_billing(total_duration_hours, daily_rate, hourly_rate)
    elif pricing_strategy == 'daily_plus_excess_hourly':
        return _calculate_daily_plus_excess_hourly_billing(total_duration_hours, daily_rate, hourly_rate)
    else:
        return Decimal('0.00')

# Calculates billing for 'flat_24_hour': any fraction of 24h rounds to a full day.
def _calculate_flat_24_hour_billing(total_duration_hours, daily_rate):
    billed_days = Decimal(ceil(float(total_duration_hours) / 24.0)).quantize(Decimal('1.'), rounding=ROUND_HALF_UP)
    return billed_days * daily_rate

# Calculates billing for '24_hour_plus_margin': excess hours within margin are free, otherwise a full day.
def _calculate_24_hour_plus_margin_billing(total_duration_hours, daily_rate, hourly_rate, excess_hours_margin):
    full_24_hour_blocks = Decimal(floor(float(total_duration_hours) / 24.0)).quantize(Decimal('1.'), rounding=ROUND_HALF_UP)
    remaining_excess_hours = total_duration_hours % 24
    additional_charge = Decimal('0.00')
    if remaining_excess_hours > Decimal('0.00') and remaining_excess_hours > Decimal(str(excess_hours_margin)):
        additional_charge = daily_rate
    return (full_24_hour_blocks * daily_rate) + additional_charge

# Calculates billing for '24_hour_customer_friendly': excess hours charged at min(hourly, daily rate).
def _calculate_24_hour_customer_friendly_billing(total_duration_hours, daily_rate, hourly_rate):
    full_24_hour_blocks = Decimal(floor(float(total_duration_hours) / 24.0)).quantize(Decimal('1.'), rounding=ROUND_HALF_UP)
    remaining_excess_hours = total_duration_hours % 24
    additional_cost = Decimal('0.00')
    if remaining_excess_hours > Decimal('0.00'):
        billed_excess_hours = Decimal(ceil(float(remaining_excess_hours))).quantize(Decimal('1.'), rounding=ROUND_HALF_UP)
        cost_by_hourly_rate = billed_excess_hours * hourly_rate
        additional_cost = min(cost_by_hourly_rate, daily_rate)
    return (full_24_hour_blocks * daily_rate) + additional_cost

# Calculates billing for 'daily_plus_excess_hourly': full days + hourly charge for any excess.
def _calculate_daily_plus_excess_hourly_billing(total_duration_hours, daily_rate, hourly_rate):
    full_24_hour_blocks = Decimal(floor(float(total_duration_hours) / 24.0)).quantize(Decimal('1.'), rounding=ROUND_HALF_UP)
    remaining_excess_hours = total_duration_hours % 24
    additional_cost = Decimal('0.00')
    if remaining_excess_hours > Decimal('0.00'):
        billed_excess_hours = Decimal(ceil(float(remaining_excess_hours))).quantize(Decimal('1.'), rounding=ROUND_HALF_UP)
        additional_cost = billed_excess_hours * hourly_rate
    return (full_24_hour_blocks * daily_rate) + additional_cost

# Calculates billable duration in days based on pricing strategy, for display or day counting.
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

    if pickup_date == return_date:
        return 1 if total_hours_float > 0 else 0

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
                return int(max(1, full_24_hour_blocks)) if total_hours_float > 0 else 0
        else:
            return int(full_24_hour_blocks) if full_24_hour_blocks > 0 else (1 if total_hours_float > 0 else 0)
    elif pricing_strategy == 'daily_plus_excess_hourly':
        full_24_hour_blocks = floor(total_hours_float / 24.0)
        return int(full_24_hour_blocks)
    else:
        return 0

# Retrieves existing bookings that conflict with a given new booking period.
def get_overlapping_motorcycle_bookings(motorcycle, pickup_date, pickup_time, return_date, return_time, exclude_booking_id=None):
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
        booking_pickup_dt = timezone.make_aware(datetime.datetime.combine(booking.pickup_date, booking.pickup_time))
        booking_return_dt = timezone.make_aware(datetime.datetime.combine(booking.return_date, booking.return_time))
        # Precise datetime overlap check
        if max(pickup_datetime, booking_pickup_dt) < min(return_datetime, booking_return_dt):
            actual_overlaps.append(booking)
    return actual_overlaps

# Checks if a motorcycle is available for a temporary booking, considering its status and other bookings.
def is_motorcycle_available(request, motorcycle, temp_booking):
    if not motorcycle.is_available:
        messages.error(request, "The selected motorcycle is currently not available.")
        return False

    if not temp_booking.pickup_date or not temp_booking.pickup_time or \
       not temp_booking.return_date or not temp_booking.return_time:
        messages.error(request, "Please select valid pickup and return dates/times first.")
        return False

    pickup_datetime = timezone.make_aware(datetime.datetime.combine(temp_booking.pickup_date, temp_booking.pickup_time))
    return_datetime = timezone.make_aware(datetime.datetime.combine(temp_booking.return_date, temp_booking.return_time))

    if return_datetime <= pickup_datetime:
        messages.error(request, "Return time must be after pickup time.")
        return False

    if motorcycle.engine_size > 50 and not temp_booking.has_motorcycle_license:
        messages.error(request, "You require a full motorcycle license for this motorcycle.")
        return False

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
