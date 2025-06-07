import datetime
from django.utils import timezone
from service.models import ServiceSettings, ServiceBooking

def get_available_dropoff_times(selected_date):
    """
    Calculates and returns a list of available drop-off times for a given date.
    This function considers:
    1. The global drop_off_start_time and drop_off_end_time from ServiceSettings,
       unless allow_after_hours_dropoff is enabled.
    2. The drop_off_spacing_mins from ServiceSettings to create intervals.
    3. Existing bookings on the selected_date and disables slots around them
       based on the drop_off_spacing_mins.
    4. If the selected_date is today, it restricts available times to be
       on or before latest_same_day_dropoff_time from ServiceSettings,
       unless allow_after_hours_dropoff is enabled.

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

    allow_after_hours_dropoff = service_settings.allow_after_hours_dropoff

    # Get the current time, which is already timezone-aware
    now = timezone.now()

    # Initialize start_time and end_time based on whether after-hours drop-off is allowed
    if allow_after_hours_dropoff:
        # If after-hours drop-off is allowed, consider the full 24 hours for potential slots
        start_time_obj = datetime.time(0, 0)  # 00:00
        end_time_obj = datetime.time(23, 59) # 23:59
    else:
        # Use standard drop-off start and end times
        start_time_obj = service_settings.drop_off_start_time
        end_time_obj = service_settings.drop_off_end_time

        # Get today's date, aware of the local timezone
        today_local = timezone.localdate(now) # This extracts the date part from the aware `now` datetime

        # If the selected date is today (or in the past), adjust the end_time
        # to latest_same_day_dropoff_time.
        if selected_date <= today_local:
            # This check is only relevant if not allowing after-hours drop-off
            if service_settings.latest_same_day_dropoff_time < end_time_obj:
                end_time_obj = service_settings.latest_same_day_dropoff_time

    spacing_minutes = service_settings.drop_off_spacing_mins

    # Initialize a list to hold all potential time slots
    potential_slots = []

    # Combine selected_date with start/end time objects to create timezone-aware datetimes
    # Explicitly make aware using the current active timezone to prevent naive/aware TypeErrors
    current_slot_datetime = timezone.make_aware(
        datetime.datetime.combine(selected_date, start_time_obj),
        timezone=timezone.get_current_timezone() # <--- Explicitly specify timezone
    )
    end_slot_datetime = timezone.make_aware(
        datetime.datetime.combine(selected_date, end_time_obj),
        timezone=timezone.get_current_timezone() # <--- Explicitly specify timezone
    )

    # Generate slots until current_slot_datetime exceeds end_slot_datetime
    while current_slot_datetime <= end_slot_datetime:
        # If selected_date is today (or in the past) and after-hours drop-off is not allowed,
        # ensure we don't suggest times that have already passed relative to `now`.
        if not allow_after_hours_dropoff and selected_date <= today_local and \
           current_slot_datetime < now: # `now` is timezone-aware
            current_slot_datetime += datetime.timedelta(minutes=spacing_minutes)
            continue # Skip past times

        potential_slots.append(current_slot_datetime.strftime('%H:%M'))
        current_slot_datetime += datetime.timedelta(minutes=spacing_minutes)

    available_slots_set = set(potential_slots) # Use a set for efficient lookup and removal

    # Retrieve existing bookings for the selected date
    # Only consider bookings that have a dropoff_time set
    bookings = ServiceBooking.objects.filter(dropoff_date=selected_date, dropoff_time__isnull=False)

    # For each booking, identify and remove slots within the blocked window
    for booking in bookings:
        # Calculate the blocked window around the booking's dropoff_time
        # Ensure booked_time_dt is also timezone-aware for consistent comparisons
        booked_time_dt = timezone.make_aware(
            datetime.datetime.combine(selected_date, booking.dropoff_time),
            timezone=timezone.get_current_timezone() # <--- Explicitly specify timezone
        )
        block_start_datetime = booked_time_dt - datetime.timedelta(minutes=spacing_minutes)
        block_end_datetime = booked_time_dt + datetime.timedelta(minutes=spacing_minutes)

        # Iterate through the potential slots and remove those within the blocked window
        slots_to_remove = set()
        for slot_str in available_slots_set:
            # Parse the slot string back to a time object
            slot_time = datetime.datetime.strptime(slot_str, '%H:%M').time()
            # Make slot_datetime timezone-aware for comparison
            slot_datetime = timezone.make_aware(
                datetime.datetime.combine(selected_date, slot_time),
                timezone=timezone.get_current_timezone() # <--- Explicitly specify timezone
            )

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