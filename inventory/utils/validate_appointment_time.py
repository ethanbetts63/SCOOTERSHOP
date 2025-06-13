# inventory/utils/validate_appointment_time.py

from datetime import date, datetime, time, timedelta

def validate_appointment_time(appointment_date: date, appointment_time: time, inventory_settings):
    errors = []

    if not inventory_settings:
        return errors

    start_time = inventory_settings.sales_appointment_start_time
    end_time = inventory_settings.sales_appointment_end_time

    if not (start_time <= appointment_time <= end_time):
        errors.append(
            f"Appointments are only available between {start_time.strftime('%I:%M %p')} and {end_time.strftime('%I:%M %p')}."
        )

    now = datetime.now()
    appointment_datetime = datetime.combine(appointment_date, appointment_time)
    min_advance_hours = inventory_settings.min_advance_booking_hours

    earliest_allowed_datetime = now + timedelta(hours=min_advance_hours)
    if appointment_datetime <= earliest_allowed_datetime:
        errors.append(
            f"The selected time is too soon. Appointments require at least {min_advance_hours} hours notice from the current time."
        )

    return errors
