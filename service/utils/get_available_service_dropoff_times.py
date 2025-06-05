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

    # Initialize a list to hold all potential time slots
    potential_slots = []
    current_slot_datetime = datetime.datetime.combine(selected_date, start_time)
    end_slot_datetime = datetime.datetime.combine(selected_date, end_time)

    # Generate all potential slots within the operational hours
    while current_slot_datetime <= end_slot_datetime:
        potential_slots.append(current_slot_datetime.time())
        current_slot_datetime += datetime.timedelta(minutes=1) # Check every minute for precise blocking

    # Convert potential slots to a set for faster lookup and removal
    available_slots_set = {slot.strftime('%H:%M') for slot in potential_slots}

    # Get existing bookings for the selected date
    # Filter by 'booked' and 'in_progress' as these occupy slots
    existing_bookings = ServiceBooking.objects.filter(
        dropoff_date=selected_date,
        booking_status__in=['booked', 'in_progress', 'confirmed']
    )

    # Block times around existing bookings
    for booking in existing_bookings:
        booked_time = booking.dropoff_time
        booked_datetime = datetime.datetime.combine(selected_date, booked_time)

        # Calculate the start and end of the blocked window
        # The window extends 'spacing_minutes' before and after the booked time
        block_start_datetime = booked_datetime - datetime.timedelta(minutes=spacing_minutes)
        block_end_datetime = booked_datetime + datetime.timedelta(minutes=spacing_minutes)

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
    if service_settings: # Ensure settings exist before using them
        start_time_dt = datetime.datetime.combine(selected_date, service_settings.drop_off_start_time)
        end_time_dt = datetime.datetime.combine(selected_date, service_settings.drop_off_end_time)
        
        current_candidate_time = start_time_dt
        while current_candidate_time <= end_time_dt:
            time_str = current_candidate_time.strftime('%H:%M')
            if time_str in available_slots_set:
                final_available_slots.append(time_str)
            current_candidate_time += datetime.timedelta(minutes=service_settings.drop_off_spacing_mins)

    return sorted(list(final_available_slots)) # Return sorted list
