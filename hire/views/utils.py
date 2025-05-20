import datetime
from django.utils import timezone

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