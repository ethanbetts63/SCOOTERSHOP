# hire/utils.py

import datetime
from django.utils import timezone
from dashboard.models import HireSettings # Assuming HireSettings is needed for calculations


def calculate_hire_duration_days(pickup_datetime, return_datetime):
     """
     Calculates the number of hire days based on pickup and return datetimes.
     Assumes any part of a day counts as a full day (e.g., pickup 10am Day 1, return 11am Day 2 = 2 days).
     Adjust this logic based on your business rules.
     """
     if not pickup_datetime or not return_datetime or return_datetime <= pickup_datetime:
         return 0 # Invalid duration

     # Calculate the difference
     duration = return_datetime - pickup_datetime

     # Calculate days. Simple floor division + 1 covers most cases where return is later than pickup time.
     # For example: Day 1 10:00 to Day 2 09:00 is 1 day difference, but should be 2 hire days.
     # Day 1 10:00 to Day 2 11:00 is 1 day difference, should be 2 hire days.
     # Day 1 10:00 to Day 1 18:00 is 0 days difference, should be 1 hire day.

     days = (return_datetime.date() - pickup_datetime.date()).days

     # Add an extra day if the return time is later than the pickup time on a subsequent day,
     # or if the hire is less than 24 hours but crosses midnight.
     # A simpler robust rule: count the number of *nights* + 1. Or use total seconds.
     # Let's use total seconds and round up based on 24-hour periods.
     total_seconds = duration.total_seconds()
     if total_seconds <= 0:
         return 0

     hours = total_seconds / 3600
     # Using math.ceil might be appropriate if any fraction of a day counts as a full day.
     # Let's use a simple logic: if hours > 0, minimum 1 day. Then add full 24hr periods.
     if hours <= 24 and hours > 0:
         return 1
     elif hours > 24:
          # Calculate full 24 hour blocks
          full_days = int(hours // 24)
          remaining_hours = hours % 24
          # Add 1 more day if there are any remaining hours
          return full_days + (1 if remaining_hours > 0 else 0)
     else:
         return 0 # Should not happen if total_seconds > 0


def calculate_hire_price(motorcycle, pickup_datetime, return_datetime, hire_settings):
    """
    Calculates the total hire price for a specific motorcycle and date range.
    Needs to implement your actual pricing logic (daily, weekly, monthly rates, discounts).
    """
    if not motorcycle or not pickup_datetime or not return_datetime or return_datetime <= pickup_datetime:
        return 0 # Invalid input

    duration_days = calculate_hire_duration_days(pickup_datetime, return_datetime)

    if duration_days <= 0:
        return 0

    # --- Your Pricing Logic Here ---
    # This is a simplified example. Replace with your actual rate calculations.

    # Get the base daily rate from the motorcycle or settings
    base_daily_rate = motorcycle.daily_hire_rate
    if base_daily_rate is None and hire_settings:
        base_daily_rate = hire_settings.default_daily_rate
    if base_daily_rate is None:
        # Fallback or raise error if no rate can be determined
        return 0 # Or handle this case as an error

    # Example: Simple daily rate multiplied by duration
    total_price = base_daily_rate * duration_days

    # Example: Apply monthly discount if duration is 30 days or more
    # You would need booked_monthly_rate on the motorcycle/settings for this
    # if duration_days >= 30 and motorcycle.monthly_hire_rate is not None:
    #      # Assuming monthly rate is simply monthly_rate / 30 days
    #      # Or calculate based on your specific monthly discount rules
    #      total_price = (motorcycle.monthly_hire_rate / 30) * duration_days
    # elif duration_days >= 30 and hire_settings and hire_settings.monthly_discount_percentage is not None:
    #      monthly_discount_factor = hire_settings.monthly_discount_percentage / 100
    #      total_price = (base_daily_rate * duration_days) * (1 - monthly_discount_factor)

    # Example: Apply weekly discount if duration is 7 days or more
    # Similar logic for weekly rates/discounts

    # Ensure calculated price is not negative (shouldn't be if rates and duration are > 0)
    return max(0, total_price)