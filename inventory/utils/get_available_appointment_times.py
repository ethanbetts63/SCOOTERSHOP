# inventory/utils/get_available_appointment_times.py

from datetime import date, datetime, timedelta

from inventory.models import SalesBooking
from inventory.utils.validate_appointment_time import validate_appointment_time # Import the enhanced time validator

def get_available_appointment_times(selected_date: date, inventory_settings):
    available_time_slots = []

    if not inventory_settings:
        return available_time_slots

    start_time_obj = inventory_settings.sales_appointment_start_time
    end_time_obj = inventory_settings.sales_appointment_end_time
    spacing_minutes = inventory_settings.sales_appointment_spacing_mins

    # 1. Generate all potential slots based on start, end, and spacing
    potential_slots_raw = []
    current_slot_time = start_time_obj
    while current_slot_time <= end_time_obj:
        potential_slots_raw.append(current_slot_time)
        dt_current_slot = datetime.combine(date.min, current_slot_time)
        dt_current_slot += timedelta(minutes=spacing_minutes)
        current_slot_time = dt_current_slot.time()

    # 2. Retrieve existing SalesBookings for the selected date
    confirmed_sales_bookings = SalesBooking.objects.filter(
        appointment_date=selected_date,
        booking_status__in=['confirmed', 'reserved'] # Only actual confirmed bookings
    ).values_list('appointment_time', flat=True)

    # Convert existing booked times to list of time objects
    existing_booked_times = list(confirmed_sales_bookings)

    # 3. Filter potential slots using the validate_appointment_time utility
    for slot_time_obj in potential_slots_raw:
        errors = validate_appointment_time(selected_date, slot_time_obj, inventory_settings, existing_booked_times)
        if not errors:
            available_time_slots.append(slot_time_obj.strftime('%H:%M')) # Add as string in HH:MM format

    return available_time_slots
