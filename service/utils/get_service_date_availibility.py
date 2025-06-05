import datetime
from django.utils import timezone
from django.conf import settings
import json

from service.models import ServiceSettings, BlockedServiceDate
# Assuming ServiceBooking model exists with a 'status' field.
# If not, you'll need to create it or adjust this logic to fit your actual model.
from service.models import ServiceBooking # Placeholder: Make sure this model exists and has a 'status' field

def get_service_date_availability():
    """
    Calculates and returns availability data for the service booking calendar.
    This includes the minimum selectable date and a list of dates/ranges to disable.

    Returns:
        tuple: A tuple containing:
            - min_date (datetime.date): The earliest date a user can select.
            - disabled_dates_json (str): JSON string of dates/ranges to disable for Flatpickr.
    """
    service_settings = ServiceSettings.objects.first()
    
    # Get current date in the Perth timezone
    now_in_perth = timezone.localtime(timezone.now()).date()

    min_date = now_in_perth
    if service_settings and service_settings.booking_advance_notice is not None:
        min_date = now_in_perth + datetime.timedelta(days=service_settings.booking_advance_notice)

    # List to hold all dates to be disabled for Flatpickr
    disabled_dates_for_flatpickr = []

    # Add blocked service dates
    blocked_dates_queryset = BlockedServiceDate.objects.all()
    for blocked_date in blocked_dates_queryset:
        disabled_dates_for_flatpickr.append({
            'from': str(blocked_date.start_date),
            'to': str(blocked_date.end_date)
        })

    # Map weekday numbers to abbreviations (Monday=0, Sunday=6)
    day_names_map = {
        0: 'Mon', 1: 'Tue', 2: 'Wed', 3: 'Thu',
        4: 'Fri', 5: 'Sat', 6: 'Sun'
    }
    
    # Iterate over a reasonable future range (e.g., next 365 days)
    # to find and disable non-open days and full-capacity days.
    # Start checking from today, or the min_date if it's in the future.
    start_checking_date = min_date
    for i in range(366): # Check for a year from the minimum allowed date
        current_check_date = start_checking_date + datetime.timedelta(days=i)
        current_day_abbr = day_names_map.get(current_check_date.weekday())
        
        # Rule: Disable non-booking open days
        if service_settings and service_settings.booking_open_days:
            open_days_list = [d.strip() for d in service_settings.booking_open_days.split(',')]
            if current_day_abbr not in open_days_list:
                disabled_dates_for_flatpickr.append(str(current_check_date))
                continue # Skip capacity check if day is already closed

        # Rule: Disable days that have reached max visible slots (capacity)
        # This assumes ServiceBooking exists and has a 'status' field.
        if service_settings and service_settings.max_visible_slots_per_day is not None:
            booked_slots_count = ServiceBooking.objects.filter(
                dropoff_date=current_check_date,
                booking_status__in=['booked', 'in_progress'] # Consider 'booked' and 'in_progress' as occupied
            ).count()

            if booked_slots_count >= service_settings.max_visible_slots_per_day:
                disabled_dates_for_flatpickr.append(str(current_check_date))

    # Flatpickr minDate will handle dates prior to min_date.
    # No need to explicitly add them to disabled_dates_for_flatpickr.

    # Serialize the disabled dates list to a JSON string
    disabled_dates_json = json.dumps(disabled_dates_for_flatpickr)

    return min_date, disabled_dates_json

