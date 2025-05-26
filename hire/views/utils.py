# hire/views/utils.py

import datetime
from django.utils import timezone
from ..models import HireBooking # Assuming HireBooking is still needed for other functions
from inventory.models import Motorcycle
from django.contrib import messages # For is_motorcycle_available
from decimal import Decimal, ROUND_HALF_UP
from math import ceil, floor
from dashboard.models import HireSettings # Direct import for HireSettings

# --- Existing Billing Strategy Calculations (Unchanged) ---
# These are used by the new _calculate_price_by_strategy helper.
def _calculate_flat_24_hour_billing(total_duration_hours, daily_rate):
    billed_days = Decimal(ceil(float(total_duration_hours) / 24.0)).quantize(Decimal('1.'), rounding=ROUND_HALF_UP)
    return billed_days * daily_rate

def _calculate_24_hour_plus_margin_billing(total_duration_hours, daily_rate, hourly_rate, excess_hours_margin):
    full_24_hour_blocks = Decimal(floor(float(total_duration_hours) / 24.0)).quantize(Decimal('1.'), rounding=ROUND_HALF_UP)
    remaining_excess_hours = total_duration_hours % 24
    additional_charge = Decimal('0.00')
    # Ensure excess_hours_margin is treated as Decimal for comparison
    if remaining_excess_hours > Decimal('0.00') and remaining_excess_hours > Decimal(str(excess_hours_margin)):
        additional_charge = daily_rate
    return (full_24_hour_blocks * daily_rate) + additional_charge

def _calculate_24_hour_customer_friendly_billing(total_duration_hours, daily_rate, hourly_rate):
    full_24_hour_blocks = Decimal(floor(float(total_duration_hours) / 24.0)).quantize(Decimal('1.'), rounding=ROUND_HALF_UP)
    remaining_excess_hours = total_duration_hours % 24
    additional_cost = Decimal('0.00')
    if remaining_excess_hours > Decimal('0.00'):
        billed_excess_hours = Decimal(ceil(float(remaining_excess_hours))).quantize(Decimal('1.'), rounding=ROUND_HALF_UP)
        cost_by_hourly_rate = billed_excess_hours * hourly_rate
        additional_cost = min(cost_by_hourly_rate, daily_rate)
    return (full_24_hour_blocks * daily_rate) + additional_cost

def _calculate_daily_plus_excess_hourly_billing(total_duration_hours, daily_rate, hourly_rate):
    full_24_hour_blocks = Decimal(floor(float(total_duration_hours) / 24.0)).quantize(Decimal('1.'), rounding=ROUND_HALF_UP)
    remaining_excess_hours = total_duration_hours % 24
    additional_cost = Decimal('0.00')
    if remaining_excess_hours > Decimal('0.00'):
        billed_excess_hours = Decimal(ceil(float(remaining_excess_hours))).quantize(Decimal('1.'), rounding=ROUND_HALF_UP)
        additional_cost = billed_excess_hours * hourly_rate
    return (full_24_hour_blocks * daily_rate) + additional_cost

# --- NEW: Core Pricing Helper ---
def _calculate_price_by_strategy(total_duration_hours, daily_rate, hourly_rate, pricing_strategy, excess_hours_margin=Decimal('0'), is_same_day_hire=False):
    """
    Calculates the price for an item based on duration, rates, and pricing strategy.
    """
    # This check assumes that if either rate is None, it's problematic for most paths.
    # Calling functions (e.g., calculate_motorcycle_hire_price) also perform this check
    # after determining specific/default rates.
    if daily_rate is None or hourly_rate is None:
        return Decimal('0.00')

    if total_duration_hours <= Decimal('0.00'):
        return Decimal('0.00')

    # NEW RULE: If the hire is not on the same day (i.e., overnight or multi-day)
    # AND the total duration is less than 24 hours, charge the daily rate.
    # This assumes daily_rate is not None at this point due to the check above.
    if not is_same_day_hire and total_duration_hours < Decimal('24.00'):
        return daily_rate # Charge the full daily rate

    # Same-day hires are billed hourly, rounded up (min 1 hour).
    # This condition (is_same_day_hire) implies total_duration_hours < 24.
    # hourly_rate is assumed not None here due to the initial check.
    if is_same_day_hire:
        billed_hours = Decimal(ceil(float(total_duration_hours))).quantize(Decimal('1.'), rounding=ROUND_HALF_UP)
        # Ensure at least 1 hour is billed for very short same-day hires if total_duration_hours > 0
        if billed_hours < Decimal('1.00') and total_duration_hours > Decimal('0.00'):
             billed_hours = Decimal('1.00')
        return billed_hours * hourly_rate

    # Multi-day hire pricing strategies (applies if not same-day and duration >= 24 hours)
    # Both daily_rate and hourly_rate are assumed not None here due to the initial check.
    if pricing_strategy == 'flat_24_hour':
        return _calculate_flat_24_hour_billing(total_duration_hours, daily_rate)
    elif pricing_strategy == '24_hour_plus_margin':
        return _calculate_24_hour_plus_margin_billing(total_duration_hours, daily_rate, hourly_rate, Decimal(str(excess_hours_margin)))
    elif pricing_strategy == '24_hour_customer_friendly':
        return _calculate_24_hour_customer_friendly_billing(total_duration_hours, daily_rate, hourly_rate)
    elif pricing_strategy == 'daily_plus_excess_hourly':
        return _calculate_daily_plus_excess_hourly_billing(total_duration_hours, daily_rate, hourly_rate)
    else:
        # Fallback: if strategy unknown, perhaps default to daily_plus_excess_hourly or simple daily
        # For now, returning 0.00 if strategy isn't matched, consider logging this.
        return Decimal('0.00')

# --- NEW AND UPDATED Price Calculation Functions ---

def calculate_motorcycle_hire_price(motorcycle, pickup_date, return_date, pickup_time, return_time, hire_settings):
    """
    Calculates the total hire price for the motorcycle based on strategy and motorcycle/default rates.
    """
    if not all([motorcycle, pickup_date, return_date, pickup_time, return_time, hire_settings]):
        return Decimal('0.00')

    pickup_datetime = datetime.datetime.combine(pickup_date, pickup_time)
    return_datetime = datetime.datetime.combine(return_date, return_time)

    if return_datetime <= pickup_datetime:
        return Decimal('0.00')

    # Use motorcycle's specific rates or fall back to defaults from HireSettings
    daily_rate = motorcycle.daily_hire_rate if motorcycle.daily_hire_rate is not None else hire_settings.default_daily_rate
    hourly_rate = motorcycle.hourly_hire_rate if motorcycle.hourly_hire_rate is not None else hire_settings.default_hourly_rate

    if daily_rate is None or hourly_rate is None:
        return Decimal('0.00') # Essential rates are missing

    total_duration_seconds = (return_datetime - pickup_datetime).total_seconds()
    total_duration_hours = Decimal(total_duration_seconds / 3600).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
    
    is_same_day_hire = pickup_date == return_date

    return _calculate_price_by_strategy(
        total_duration_hours,
        daily_rate,
        hourly_rate,
        hire_settings.hire_pricing_strategy,
        hire_settings.excess_hours_margin,
        is_same_day_hire
    )

def calculate_package_price(package_instance, pickup_date, return_date, pickup_time, return_time, hire_settings):
    """
    Calculates the price for a single package based on its own rates and the booking duration/strategy.
    """
    if not all([package_instance, pickup_date, return_date, pickup_time, return_time, hire_settings]):
        return Decimal('0.00')
    
    # Use package's own hourly_cost and daily_cost
    daily_rate = package_instance.daily_cost
    hourly_rate = package_instance.hourly_cost

    if daily_rate is None or hourly_rate is None:
        return Decimal('0.00')

    pickup_datetime = datetime.datetime.combine(pickup_date, pickup_time)
    return_datetime = datetime.datetime.combine(return_date, return_time)

    if return_datetime <= pickup_datetime:
        return Decimal('0.00')

    total_duration_seconds = (return_datetime - pickup_datetime).total_seconds()
    total_duration_hours = Decimal(total_duration_seconds / 3600).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
    is_same_day_hire = pickup_date == return_date
    
    return _calculate_price_by_strategy(
        total_duration_hours,
        daily_rate, # package.daily_cost
        hourly_rate, # package.hourly_cost
        hire_settings.hire_pricing_strategy,
        hire_settings.excess_hours_margin,
        is_same_day_hire
    )

def calculate_addon_price(addon_instance, quantity, pickup_date, return_date, pickup_time, return_time, hire_settings):
    """
    Calculates the price for a given quantity of a single add-on.
    """
    if not all([addon_instance, quantity, pickup_date, return_date, pickup_time, return_time, hire_settings]):
        return Decimal('0.00')
    if quantity <= 0:
        return Decimal('0.00')

    # Use addon's own hourly_cost and daily_cost
    daily_rate = addon_instance.daily_cost
    hourly_rate = addon_instance.hourly_cost

    if daily_rate is None or hourly_rate is None:
        return Decimal('0.00')

    pickup_datetime = datetime.datetime.combine(pickup_date, pickup_time)
    return_datetime = datetime.datetime.combine(return_date, return_time)

    if return_datetime <= pickup_datetime:
        return Decimal('0.00')

    total_duration_seconds = (return_datetime - pickup_datetime).total_seconds()
    total_duration_hours = Decimal(total_duration_seconds / 3600).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
    is_same_day_hire = pickup_date == return_date

    # Calculate price for one unit of the addon
    single_addon_unit_price = _calculate_price_by_strategy(
        total_duration_hours,
        daily_rate, # addon.daily_cost
        hourly_rate, # addon.hourly_cost
        hire_settings.hire_pricing_strategy,
        hire_settings.excess_hours_margin,
        is_same_day_hire
    )
    
    return single_addon_unit_price * Decimal(str(quantity))


def calculate_total_addons_price(temp_booking, hire_settings):
    """
    Calculates the total price for all add-ons in a temporary booking.
    """
    if not temp_booking or not hire_settings:
        return Decimal('0.00')
    if not temp_booking.pickup_date or not temp_booking.return_date or \
       not temp_booking.pickup_time or not temp_booking.return_time: # Dates from TempHireBooking
        return Decimal('0.00') # Dates must be set

    total_price = Decimal('0.00')
    # temp_booking_addons is a related name from TempBookingAddOn to TempHireBooking
    for temp_booking_addon in temp_booking.temp_booking_addons.all(): # Accesses related TempBookingAddOn instances
        if temp_booking_addon.addon and temp_booking_addon.quantity > 0: # addon and quantity from TempBookingAddOn
            total_price += calculate_addon_price(
                addon_instance=temp_booking_addon.addon,
                quantity=temp_booking_addon.quantity,
                pickup_date=temp_booking.pickup_date,
                return_date=temp_booking.return_date,
                pickup_time=temp_booking.pickup_time,
                return_time=temp_booking.return_time,
                hire_settings=hire_settings
            )
    return total_price

def calculate_booking_grand_total(temp_booking, hire_settings):
    """
    Calculates the grand total for a temporary booking, including motorcycle, package, and add-ons.
    Returns a dictionary with individual components and the grand total.
    """
    if not temp_booking or not hire_settings:
        return {
            'motorcycle_price': Decimal('0.00'),
            'package_price': Decimal('0.00'),
            'addons_total_price': Decimal('0.00'),
            'grand_total': Decimal('0.00'),
        }

    motorcycle_total_price = Decimal('0.00')
    package_total_price = Decimal('0.00')
    addons_total_price = Decimal('0.00')

    # Ensure necessary date/time fields are present on temp_booking
    if temp_booking.pickup_date and temp_booking.pickup_time and \
       temp_booking.return_date and temp_booking.return_time:

        # 1. Calculate Motorcycle Hire Price
        if temp_booking.motorcycle: # motorcycle field in TempHireBooking
            motorcycle_total_price = calculate_motorcycle_hire_price(
                motorcycle=temp_booking.motorcycle,
                pickup_date=temp_booking.pickup_date,
                return_date=temp_booking.return_date,
                pickup_time=temp_booking.pickup_time,
                return_time=temp_booking.return_time,
                hire_settings=hire_settings
            )

        # 2. Calculate Package Price
        if temp_booking.package: # package field in TempHireBooking
            package_total_price = calculate_package_price(
                package_instance=temp_booking.package,
                pickup_date=temp_booking.pickup_date,
                return_date=temp_booking.return_date,
                pickup_time=temp_booking.pickup_time,
                return_time=temp_booking.return_time,
                hire_settings=hire_settings
            )
            # Note: The temp_booking.booked_package_price should be updated
            # with this value where this function is called.

        # 3. Calculate Total Add-ons Price
        if temp_booking.temp_booking_addons.exists(): # temp_booking_addons is the related_name
            addons_total_price = calculate_total_addons_price(
                temp_booking=temp_booking,
                hire_settings=hire_settings
            )
            # Note: temp_booking.total_addons_price should be updated
            # with this value where this function is called.
    
    grand_total = motorcycle_total_price + package_total_price + addons_total_price

    return {
        'motorcycle_price': motorcycle_total_price, # Corresponds to total_hire_price in TempHireBooking
        'package_price': package_total_price,      # Corresponds to total_package_price in TempHireBooking
        'addons_total_price': addons_total_price,  # Corresponds to total_addons_price in TempHireBooking
        'grand_total': grand_total,                # Corresponds to grand_total in TempHireBooking
    }


# --- Existing Utility Functions (Largely Unchanged but may need review for dependencies) ---

# Calculates billable duration in days based on pricing strategy, for display or day counting.
def calculate_hire_duration_days(motorcycle, pickup_date, return_date, pickup_time, return_time, hire_settings):
    # This function's logic might need to align with how _calculate_price_by_strategy effectively counts days
    # For now, keeping it as it was in the provided file
    pickup_datetime = datetime.datetime.combine(pickup_date, pickup_time)
    return_datetime = datetime.datetime.combine(return_date, return_time)

    if return_datetime <= pickup_datetime:
        return 0

    pricing_strategy = hire_settings.hire_pricing_strategy 
    total_duration_seconds = (return_datetime - pickup_datetime).total_seconds()
    total_hours_float = total_duration_seconds / 3600.0

    daily_rate = motorcycle.daily_hire_rate if motorcycle.daily_hire_rate is not None else hire_settings.default_daily_rate
    hourly_rate = motorcycle.hourly_hire_rate if motorcycle.hourly_hire_rate is not None else hire_settings.default_hourly_rate

    if pickup_date == return_date: # Same-day hire
        return 1 if total_hours_float > 0 else 0 # Counts as 1 day if any duration

    # For multi-day hires, the definition of a "day" for display can vary
    if pricing_strategy == 'flat_24_hour':
        return int(ceil(total_hours_float / 24.0))
    elif pricing_strategy == '24_hour_plus_margin':
        full_24_hour_blocks = floor(total_hours_float / 24.0)
        remaining_excess_hours_float = total_hours_float % 24.0
        margin_hours_float = float(hire_settings.excess_hours_margin) 
        if remaining_excess_hours_float > 0.0 and remaining_excess_hours_float > margin_hours_float:
            return int(full_24_hour_blocks + 1)
        else: # If within margin or no excess
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
        if booking.pickup_time is None or booking.return_time is None:
            continue

        booking_pickup_dt = timezone.make_aware(datetime.datetime.combine(booking.pickup_date, booking.pickup_time))
        booking_return_dt = timezone.make_aware(datetime.datetime.combine(booking.return_date, booking.return_time))
        
        if pickup_datetime < booking_return_dt and booking_pickup_dt < return_datetime:
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

    if datetime.datetime.combine(temp_booking.return_date, temp_booking.return_time) <= \
       datetime.datetime.combine(temp_booking.pickup_date, temp_booking.pickup_time):
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
