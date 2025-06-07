from django.utils import timezone
from datetime import timedelta, datetime
from service.models import BlockedServiceDate # Assuming BlockedServiceDate is in service.models

def get_drop_off_date_availability(temp_booking, service_settings):
    """
    Calculates a list of all available drop-off dates based on the temporary booking's
    service date, global service settings, and blocked service dates.

    Args:
        temp_booking (TempServiceBooking): The temporary service booking instance,
                                          containing the 'service_date'.
        service_settings (ServiceSettings): The singleton service settings instance,
                                            containing 'max_advance_dropoff_days',
                                            'allow_after_hours_dropoff', and
                                            'booking_open_days'.

    Returns:
        list: A list of date strings (YYYY-MM-DD) representing all valid drop-off dates.
              Returns an empty list if no dates are available or valid.
    """
    today = timezone.localdate(timezone.now())
    service_date = temp_booking.service_date
    max_advance_days = service_settings.max_advance_dropoff_days
    allow_after_hours_dropoff = service_settings.allow_after_hours_dropoff
    booking_open_days_str = service_settings.booking_open_days

    # Map weekday names to datetime.date.weekday() integers (Monday is 0, Sunday is 6)
    day_name_to_weekday_num = {
        "Mon": 0, "Tue": 1, "Wed": 2, "Thu": 3, "Fri": 4, "Sat": 5, "Sun": 6
    }
    # Parse booking_open_days into a set of weekday numbers for efficient lookup
    # Handle cases where booking_open_days_str might be empty or malformed
    if booking_open_days_str:
        booking_open_weekdays = {
            day_name_to_weekday_num[day.strip()]
            for day in booking_open_days_str.split(',')
            if day.strip() in day_name_to_weekday_num
        }
    else:
        booking_open_weekdays = set() # No days are open if string is empty/invalid


    # Drop-off date cannot be after the scheduled service date
    calculated_max_dropoff_date = service_date
    
    # Calculate the earliest possible drop-off date
    # This date is 'max_advance_days' before the service_date
    calculated_min_dropoff_date = service_date - timedelta(days=max_advance_days)

    # Ensure the earliest allowed date is not in the past relative to today
    if calculated_min_dropoff_date < today:
        calculated_min_dropoff_date = today

    available_dates = []

    # If the calculated min date is after the max date, no dates are available
    if calculated_min_dropoff_date > calculated_max_dropoff_date:
        return []

    # Fetch all blocked service dates that might overlap with our potential range
    # Get all blocked dates that start before or on calculated_max_dropoff_date
    # AND end after or on calculated_min_dropoff_date
    blocked_dates = BlockedServiceDate.objects.filter(
        start_date__lte=calculated_max_dropoff_date,
        end_date__gte=calculated_min_dropoff_date
    ).values_list('start_date', 'end_date')

    # Create a set of all individual blocked dates for quick lookup
    # Note: This could be memory-intensive for very large blocked ranges.
    # For typical use cases (e.g., a few months out), it's fine.
    # If blocked ranges are very long (years), a more optimized approach might be needed.
    blocked_date_set = set()
    for start, end in blocked_dates:
        current_blocked_day = start
        while current_blocked_day <= end:
            blocked_date_set.add(current_blocked_day)
            current_blocked_day += timedelta(days=1)

    current_date = calculated_min_dropoff_date
    while current_date <= calculated_max_dropoff_date:
        # Check if the current date is not blocked
        if current_date not in blocked_date_set:
            # If after-hours drop-off is NOT allowed, filter by booking open days
            if not allow_after_hours_dropoff:
                if current_date.weekday() in booking_open_weekdays:
                    available_dates.append(current_date.strftime('%Y-%m-%d'))
            else:
                # If after-hours drop-off IS allowed, add the date regardless of open days
                available_dates.append(current_date.strftime('%Y-%m-%d'))
        
        current_date += timedelta(days=1)

    return available_dates

