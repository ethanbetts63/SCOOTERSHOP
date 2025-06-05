import datetime
from django.utils import timezone
from service.models import ServiceSettings, ServiceBooking

def get_available_dropoff_times(selected_date):
    """
    Calculates and returns a list of available drop-off times for a given date.
    This function considers:
    1. The global drop_off_start_time and drop_off_end_time from ServiceSettings.
    2. The drop_off_spacing_mins from ServiceSettings to create intervals.
    3. Existing bookings on the selected_date and disables slots around them
       based on the drop_off_spacing_mins.
    4. If the selected_date is today, it restricts available times to be
       on or before latest_same_day_dropoff_time from ServiceSettings.

    Args:
        selected_date (datetime.date): The date for which to find available times.

    Returns:
        list: A list of strings, each representing an available time slot in "HH:MM" format.
              Returns an empty list if no settings are found or no slots are available.
    """
    service_settings = ServiceSettings.objects.first()
    if not service_settings:
        # If no service settings exist, no times can be generated.
        return []

    start_time = service_settings.drop_off_start_time
    end_time = service_settings.drop_off_end_time
    spacing_minutes = service_settings.drop_off_spacing_mins

    # If the selected date is today, adjust the end_time to latest_same_day_dropoff_time
    # This also applies if selected_date is in the past, though ideally UI prevents this.
    today = timezone.localdate(timezone.now())
    if selected_date <= today:
        if service_settings.latest_same_day_dropoff_time < end_time:
            end_time = service_settings.latest_same_day_dropoff_time

    # Initialize a list to hold all potential time slots
    potential_slots = []
    current_slot_datetime = datetime.datetime.combine(selected_date, start_time)
    end_slot_datetime = datetime.datetime.combine(selected_date, end_time)

    while current_slot_datetime <= end_slot_datetime:
        potential_slots.append(current_slot_datetime.strftime('%H:%M'))
        current_slot_datetime += datetime.timedelta(minutes=spacing_minutes)

    available_slots_set = set(potential_slots) # Use a set for efficient lookup and removal

    # Retrieve existing bookings for the selected date
    bookings = ServiceBooking.objects.filter(dropoff_date=selected_date)

    # For each booking, identify and remove slots within the blocked window
    for booking in bookings:
        # Calculate the blocked window around the booking's dropoff_time
        booked_time_dt = datetime.datetime.combine(selected_date, booking.dropoff_time)
        block_start_datetime = booked_time_dt - datetime.timedelta(minutes=spacing_minutes)
        block_end_datetime = booked_time_dt + datetime.timedelta(minutes=spacing_minutes)

        # Iterate through the potential slots and remove those within the blocked window
        # We need to iterate over a copy of the set or build a new one to avoid modifying during iteration
        slots_to_remove = set()
        for slot_str in available_slots_set:
            # Parse the slot string back to a time object
            slot_time = datetime.datetime.strptime(slot_str, '%H:%M').time()
            slot_datetime = datetime.datetime.combine(selected_date, slot_time)

            if block_start_datetime <= slot_datetime <= block_end_datetime:
                slots_to_remove.add(slot_str)
        
        available_slots_set -= slots_to_remove # Remove all identified blocked slots
        
    final_available_slots = []
    # Re-iterate through the original potential slots (in order) and add only the available ones
    # This ensures the final list is sorted chronologically
    for slot_str in potential_slots:
        if slot_str in available_slots_set:
            final_available_slots.append(slot_str)

    return final_available_slots
