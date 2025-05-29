# hire/views/hire_pricing.py

import datetime
from django.utils import timezone
from .models import HireBooking
from inventory.models import Motorcycle
from django.contrib import messages
from decimal import Decimal, ROUND_HALF_UP
from math import ceil, floor
from dashboard.models import HireSettings

def _calculate_flat_24_hour_billing(total_duration_hours, daily_rate):
    # Any portion of a 24-hour period is rounded up to a full day.
    billed_days = Decimal(ceil(float(total_duration_hours) / 24.0)).quantize(Decimal('1.'), rounding=ROUND_HALF_UP)
    return billed_days * daily_rate

def _calculate_24_hour_plus_margin_billing(total_duration_hours, daily_rate, hourly_rate, excess_hours_margin):
    # Charges for full 24-hour blocks, plus an additional full day if excess hours exceed a margin.
    full_24_hour_blocks = Decimal(floor(float(total_duration_hours) / 24.0)).quantize(Decimal('1.'), rounding=ROUND_HALF_UP)
    remaining_excess_hours = total_duration_hours % 24
    additional_charge = Decimal('0.00')
    if remaining_excess_hours > Decimal('0.00') and remaining_excess_hours > Decimal(str(excess_hours_margin)):
        additional_charge = daily_rate
    return (full_24_hour_blocks * daily_rate) + additional_charge

def _calculate_24_hour_customer_friendly_billing(total_duration_hours, daily_rate, hourly_rate):
    # Charges for full 24-hour blocks, then the cheaper of hourly rate for excess or full daily rate.
    full_24_hour_blocks = Decimal(floor(float(total_duration_hours) / 24.0)).quantize(Decimal('1.'), rounding=ROUND_HALF_UP)
    remaining_excess_hours = total_duration_hours % 24
    additional_cost = Decimal('0.00')
    if remaining_excess_hours > Decimal('0.00'):
        billed_excess_hours = Decimal(ceil(float(remaining_excess_hours))).quantize(Decimal('1.'), rounding=ROUND_HALF_UP)
        cost_by_hourly_rate = billed_excess_hours * hourly_rate
        additional_cost = min(cost_by_hourly_rate, daily_rate)
    return (full_24_hour_blocks * daily_rate) + additional_cost

def _calculate_daily_plus_excess_hourly_billing(total_duration_hours, daily_rate, hourly_rate):
    # Charges for full 24-hour blocks at daily rate, plus excess hours at hourly rate.
    full_24_hour_blocks = Decimal(floor(float(total_duration_hours) / 24.0)).quantize(Decimal('1.'), rounding=ROUND_HALF_UP)
    remaining_excess_hours = total_duration_hours % 24
    additional_cost = Decimal('0.00')
    if remaining_excess_hours > Decimal('0.00'):
        billed_excess_hours = Decimal(ceil(float(remaining_excess_hours))).quantize(Decimal('1.'), rounding=ROUND_HALF_UP)
        additional_cost = billed_excess_hours * hourly_rate
    return (full_24_hour_blocks * daily_rate) + additional_cost

def _calculate_daily_plus_proportional_excess_billing(total_duration_hours, daily_rate):
    # Charges for full 24-hour blocks, plus a proportional amount of the daily rate for excess hours.
    full_24_hour_blocks = Decimal(floor(float(total_duration_hours) / 24.0)).quantize(Decimal('1.'), rounding=ROUND_HALF_UP)
    remaining_excess_hours = total_duration_hours % 24
    additional_cost = Decimal('0.00')

    if remaining_excess_hours > Decimal('0.00'):
        # Calculate the percentage of a day taken by excess hours
        excess_percentage_of_day = remaining_excess_hours / Decimal('24.00')
        additional_cost = excess_percentage_of_day * daily_rate
        additional_cost = additional_cost.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP) # Quantize to 2 decimal places

    return (full_24_hour_blocks * daily_rate) + additional_cost

def _calculate_24_hour_plus_margin_proportional_billing(total_duration_hours, daily_rate, excess_hours_margin):
    # Charges for full 24-hour blocks. If excess hours exceed a margin,
    # the hours beyond the margin are charged proportionally based on the daily rate.
    full_24_hour_blocks = Decimal(floor(float(total_duration_hours) / 24.0)).quantize(Decimal('1.'), rounding=ROUND_HALF_UP)
    remaining_excess_hours = total_duration_hours % 24
    additional_charge = Decimal('0.00')

    if remaining_excess_hours > Decimal('0.00') and remaining_excess_hours > Decimal(str(excess_hours_margin)):
        # Calculate the hours to be proportionally billed (hours beyond the margin)
        billable_excess_hours = remaining_excess_hours - Decimal(str(excess_hours_margin))
        if billable_excess_hours > Decimal('0.00'):
            excess_percentage_of_day = billable_excess_hours / Decimal('24.00')
            additional_charge = excess_percentage_of_day * daily_rate
            additional_charge = additional_charge.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP) # Quantize to 2 decimal places

    return (full_24_hour_blocks * daily_rate) + additional_charge

def _calculate_price_by_strategy(total_duration_hours, daily_rate, hourly_rate, pricing_strategy, excess_hours_margin=Decimal('0'), is_same_day_hire=False):
    # Returns 0.00 if essential rates are missing or duration is non-positive.
    if daily_rate is None or hourly_rate is None:
        return Decimal('0.00')

    if total_duration_hours <= Decimal('0.00'):
        return Decimal('0.00')

    # If not a same-day hire and duration is less than 24 hours, charge a full daily rate.
    if not is_same_day_hire and total_duration_hours < Decimal('24.00'):
        return daily_rate

    # Same-day hires are billed hourly, rounded up to the nearest whole hour (minimum 1 hour).
    if is_same_day_hire:
        billed_hours = Decimal(ceil(float(total_duration_hours))).quantize(Decimal('1.'), rounding=ROUND_HALF_UP)
        if billed_hours < Decimal('1.00') and total_duration_hours > Decimal('0.00'):
             billed_hours = Decimal('1.00')
        return billed_hours * hourly_rate

    # Applies selected pricing strategy for multi-day hires (duration >= 24 hours).
    if pricing_strategy == 'flat_24_hour':
        return _calculate_flat_24_hour_billing(total_duration_hours, daily_rate)
    elif pricing_strategy == '24_hour_plus_margin':
        return _calculate_24_hour_plus_margin_billing(total_duration_hours, daily_rate, hourly_rate, Decimal(str(excess_hours_margin)))
    elif pricing_strategy == '24_hour_customer_friendly':
        return _calculate_24_hour_customer_friendly_billing(total_duration_hours, daily_rate, hourly_rate)
    elif pricing_strategy == 'daily_plus_excess_hourly':
        return _calculate_daily_plus_excess_hourly_billing(total_duration_hours, daily_rate, hourly_rate)
    elif pricing_strategy == 'daily_plus_proportional_excess':
        return _calculate_daily_plus_proportional_excess_billing(total_duration_hours, daily_rate)
    elif pricing_strategy == '24_hour_plus_margin_proportional':
        return _calculate_24_hour_plus_margin_proportional_billing(total_duration_hours, daily_rate, Decimal(str(excess_hours_margin)))
    else:
        return Decimal('0.00')

def calculate_motorcycle_hire_price(motorcycle, pickup_date, return_date, pickup_time, return_time, hire_settings):
    # Returns 0.00 if essential inputs are missing or duration is non-positive.
    if not all([motorcycle, pickup_date, return_date, pickup_time, return_time, hire_settings]):
        return Decimal('0.00')

    pickup_datetime = datetime.datetime.combine(pickup_date, pickup_time)
    return_datetime = datetime.datetime.combine(return_date, return_time)

    if return_datetime <= pickup_datetime:
        return Decimal('0.00')

    # Uses motorcycle's specific rates or falls back to default rates from HireSettings.
    daily_rate = motorcycle.daily_hire_rate if motorcycle.daily_hire_rate is not None else hire_settings.default_daily_rate
    hourly_rate = motorcycle.hourly_hire_rate if motorcycle.hourly_hire_rate is not None else hire_settings.default_hourly_rate

    if daily_rate is None or hourly_rate is None:
        return Decimal('0.00')

    # Calculates total duration in hours.
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
    # Returns 0.00 if essential inputs are missing or duration is non-positive.
    if not all([package_instance, pickup_date, return_date, pickup_time, return_time, hire_settings]):
        return Decimal('0.00')
    
    # Uses package's own daily and hourly costs.
    daily_rate = package_instance.daily_cost
    hourly_rate = package_instance.hourly_cost

    if daily_rate is None or hourly_rate is None:
        return Decimal('0.00')

    pickup_datetime = datetime.datetime.combine(pickup_date, pickup_time)
    return_datetime = datetime.datetime.combine(return_date, return_time)

    if return_datetime <= pickup_datetime:
        return Decimal('0.00')

    # Calculates total duration in hours.
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

def calculate_addon_price(addon_instance, quantity, pickup_date, return_date, pickup_time, return_time, hire_settings):
    # Returns 0.00 if essential inputs are missing, quantity is non-positive, or duration is non-positive.
    if not all([addon_instance, quantity, pickup_date, return_date, pickup_time, return_time, hire_settings]):
        return Decimal('0.00')
    if quantity <= 0:
        return Decimal('0.00')

    # Uses add-on's own daily and hourly costs.
    daily_rate = addon_instance.daily_cost
    hourly_rate = addon_instance.hourly_cost

    if daily_rate is None or hourly_rate is None:
        return Decimal('0.00')

    pickup_datetime = datetime.datetime.combine(pickup_date, pickup_time)
    return_datetime = datetime.datetime.combine(return_date, return_time)

    if return_datetime <= pickup_datetime:
        return Decimal('0.00')

    # Calculates total duration in hours.
    total_duration_seconds = (return_datetime - pickup_datetime).total_seconds()
    total_duration_hours = Decimal(total_duration_seconds / 3600).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
    is_same_day_hire = pickup_date == return_date

    # Calculates price for a single unit of the add-on, then multiplies by quantity.
    single_addon_unit_price = _calculate_price_by_strategy(
        total_duration_hours,
        daily_rate,
        hourly_rate,
        hire_settings.hire_pricing_strategy,
        hire_settings.excess_hours_margin,
        is_same_day_hire
    )
    
    return single_addon_unit_price * Decimal(str(quantity))


def calculate_total_addons_price(temp_booking, hire_settings):
    # Returns 0.00 if essential booking/settings data or dates are missing.
    if not temp_booking or not hire_settings:
        return Decimal('0.00')
    if not temp_booking.pickup_date or not temp_booking.return_date or \
       not temp_booking.pickup_time or not temp_booking.return_time:
        return Decimal('0.00')

    total_price = Decimal('0.00')
    # Iterates through each add-on in the temporary booking and sums their calculated prices.
    for temp_booking_addon in temp_booking.temp_booking_addons.all():
        if temp_booking_addon.addon and temp_booking_addon.quantity > 0:
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
    # Returns 0.00 for all components if essential booking/settings data is missing.
    if not temp_booking or not hire_settings:
        return {
            'motorcycle_price': Decimal('0.00'),
            'package_price': Decimal('0.00'),
            'addons_total_price': Decimal('0.00'),
            'grand_total': Decimal('0.00'),
            'deposit_amount': Decimal('0.00'), # Ensure deposit_amount is always returned
            'currency': 'AUD', # Default currency
        }

    motorcycle_total_price = Decimal('0.00')
    package_total_price = Decimal('0.00')
    addons_total_price = Decimal('0.00')

    # Only proceeds with calculations if all necessary date/time fields are present.
    if temp_booking.pickup_date and temp_booking.pickup_time and \
       temp_booking.return_date and temp_booking.return_time:

        # Calculates motorcycle hire price.
        if temp_booking.motorcycle:
            motorcycle_total_price = calculate_motorcycle_hire_price(
                motorcycle=temp_booking.motorcycle,
                pickup_date=temp_booking.pickup_date,
                return_date=temp_booking.return_date,
                pickup_time=temp_booking.pickup_time,
                return_time=temp_booking.return_time,
                hire_settings=hire_settings
            )

        # Calculates package price.
        if temp_booking.package:
            package_total_price = calculate_package_price(
                package_instance=temp_booking.package,
                pickup_date=temp_booking.pickup_date,
                return_date=temp_booking.return_date,
                pickup_time=temp_booking.pickup_time,
                return_time=temp_booking.return_time,
                hire_settings=hire_settings
            )

        # Calculates total add-ons price.
        if temp_booking.temp_booking_addons.exists():
            addons_total_price = calculate_total_addons_price(
                temp_booking=temp_booking,
                hire_settings=hire_settings
            )
    
    # Sums motorcycle, package, and add-on prices for the grand total.
    grand_total = motorcycle_total_price + package_total_price + addons_total_price

    # Calculate deposit amount based on hire_settings.default_deposit_calculation_method
    deposit_amount = Decimal('0.00')
    if hire_settings.deposit_enabled:
        if hire_settings.default_deposit_calculation_method == 'percentage' and hire_settings.deposit_percentage is not None:
            deposit_percentage = Decimal(str(hire_settings.deposit_percentage)) / Decimal('100')
            deposit_amount = grand_total * deposit_percentage
            deposit_amount = deposit_amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        elif hire_settings.default_deposit_calculation_method == 'fixed' and hire_settings.deposit_amount is not None:
            deposit_amount = hire_settings.deposit_amount
            deposit_amount = deposit_amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    # Get currency from hire settings, default to AUD if not set
    currency = hire_settings.currency_code if hire_settings.currency_code else 'AUD'

    return {
        'motorcycle_price': motorcycle_total_price,
        'package_price': package_total_price,
        'addons_total_price': addons_total_price,
        'grand_total': grand_total,
        'deposit_amount': deposit_amount,
        'currency': currency,
    }