import datetime
from django.utils import timezone
from service.models import ServiceSettings, ServiceBooking


def get_available_dropoff_times(selected_date):
    """
    Calculates available drop-off time slots for a given date based on service settings,
    excluding times that are already booked or in the past for same-day bookings.
    """
    service_settings = ServiceSettings.objects.first()
    if not service_settings:
        return []

    now = timezone.now()
    today_local = timezone.localdate(now)

    start_time_obj = service_settings.drop_off_start_time
    end_time_obj = service_settings.drop_off_end_time

    # Adjust end time for same-day drop-offs if a specific latest time is set
    if selected_date <= today_local:
        if service_settings.latest_same_day_dropoff_time < end_time_obj:
            end_time_obj = service_settings.latest_same_day_dropoff_time

    spacing_minutes = service_settings.drop_off_spacing_mins
    potential_slots = []

    current_slot_datetime = timezone.make_aware(
        datetime.datetime.combine(selected_date, start_time_obj),
        timezone.get_current_timezone(),
    )
    end_slot_datetime = timezone.make_aware(
        datetime.datetime.combine(selected_date, end_time_obj),
        timezone.get_current_timezone(),
    )

    # Generate potential time slots
    while current_slot_datetime <= end_slot_datetime:
        # For today's date, ensure the slot is not in the past
        if selected_date <= today_local and current_slot_datetime < now:
            current_slot_datetime += datetime.timedelta(minutes=spacing_minutes)
            continue

        potential_slots.append(current_slot_datetime.strftime("%H:%M"))
        current_slot_datetime += datetime.timedelta(minutes=spacing_minutes)

    available_slots_set = set(potential_slots)

    # Get existing bookings for the selected date
    bookings = ServiceBooking.objects.filter(
        dropoff_date=selected_date, dropoff_time__isnull=False
    )

    # Remove slots that are too close to existing bookings
    for booking in bookings:
        booked_time_dt = timezone.make_aware(
            datetime.datetime.combine(selected_date, booking.dropoff_time),
            timezone.get_current_timezone(),
        )

        # Define a buffer around the booked time to avoid back-to-back appointments
        block_start_datetime = booked_time_dt - datetime.timedelta(
            minutes=spacing_minutes
        )
        block_end_datetime = booked_time_dt + datetime.timedelta(
            minutes=spacing_minutes
        )

        slots_to_remove = set()
        for slot_str in available_slots_set:
            slot_time = datetime.datetime.strptime(slot_str, "%H:%M").time()
            slot_datetime = timezone.make_aware(
                datetime.datetime.combine(selected_date, slot_time),
                timezone.get_current_timezone(),
            )
            if block_start_datetime <= slot_datetime <= block_end_datetime:
                slots_to_remove.add(slot_str)

        available_slots_set -= slots_to_remove

    # Preserve the original order of potential slots
    final_available_slots = [
        slot for slot in potential_slots if slot in available_slots_set
    ]

    return final_available_slots
