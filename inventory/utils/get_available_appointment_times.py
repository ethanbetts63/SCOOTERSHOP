from datetime import date, datetime, timedelta
from django.utils import timezone

from inventory.models import SalesBooking
from inventory.utils.validate_appointment_time import validate_appointment_time


def get_available_appointment_times(selected_date: date, inventory_settings):
    available_time_slots = []

    if not inventory_settings:
        return available_time_slots

    now_aware = timezone.now()
    min_advance_hours = inventory_settings.min_advance_booking_hours
    earliest_allowed_datetime = now_aware + timedelta(hours=min_advance_hours)

    start_time_obj = inventory_settings.sales_appointment_start_time
    end_time_obj = inventory_settings.sales_appointment_end_time
    spacing_minutes = inventory_settings.sales_appointment_spacing_mins

    potential_slots_raw = []
    current_slot_time = start_time_obj
    while current_slot_time <= end_time_obj:
        potential_slots_raw.append(current_slot_time)
        dt_current_slot = datetime.combine(date.min, current_slot_time)
        dt_current_slot += timedelta(minutes=spacing_minutes)
        current_slot_time = dt_current_slot.time()

    confirmed_sales_bookings = SalesBooking.objects.filter(
        appointment_date=selected_date, booking_status__in=["confirmed", "reserved"]
    ).values_list("appointment_time", flat=True)

    existing_booked_times = list(confirmed_sales_bookings)

    for slot_time_obj in potential_slots_raw:
        # Combine selected date and slot time to create a datetime object
        slot_datetime = datetime.combine(selected_date, slot_time_obj)
        # Make it timezone-aware
        slot_datetime_aware = timezone.make_aware(
            slot_datetime, timezone.get_current_timezone()
        )

        # Skip times that are earlier than the minimum advance booking time
        if slot_datetime_aware < earliest_allowed_datetime:
            continue

        errors = validate_appointment_time(
            selected_date, slot_time_obj, inventory_settings, existing_booked_times
        )
        if not errors:
            available_time_slots.append(slot_time_obj.strftime("%H:%M"))

    return available_time_slots
