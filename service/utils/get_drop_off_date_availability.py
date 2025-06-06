from django.utils import timezone
from datetime import timedelta, datetime

def get_drop_off_date_availability(temp_booking, service_settings):
    """
    Calculates a list of all available drop-off dates based on the temporary booking's
    service date and global service settings.

    Args:
        temp_booking (TempServiceBooking): The temporary service booking instance,
                                          containing the 'service_date'.
        service_settings (ServiceSettings): The singleton service settings instance,
                                            containing 'max_advance_dropoff_days'.

    Returns:
        list: A list of date strings (YYYY-MM-DD) representing all valid drop-off dates.
              Returns an empty list if no dates are available or valid.
    """
    today = timezone.localdate(timezone.now())
    service_date = temp_booking.service_date
    max_advance_days = service_settings.max_advance_dropoff_days

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

    current_date = calculated_min_dropoff_date
    while current_date <= calculated_max_dropoff_date:
        available_dates.append(current_date.strftime('%Y-%m-%d'))
        current_date += timedelta(days=1)

    return available_dates

