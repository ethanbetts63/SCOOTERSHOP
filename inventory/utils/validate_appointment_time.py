# inventory/utils/validate_appointment_time.py

from datetime import date, datetime, time, timedelta
from django.utils import timezone

def validate_appointment_time(appointment_date: date, appointment_time: time, inventory_settings, existing_booked_times: list):
    errors = []

    if not inventory_settings:
        return errors

    start_time = inventory_settings.sales_appointment_start_time
    end_time = inventory_settings.sales_appointment_end_time
    spacing_minutes = inventory_settings.sales_appointment_spacing_mins

    if not (start_time <= appointment_time <= end_time):
        errors.append(
            f"Appointments are only available between {start_time.strftime('%I:%M %p')} and {end_time.strftime('%I:%M %p')}."
        )

    now_aware = timezone.now()
    appointment_datetime_aware = timezone.make_aware(datetime.combine(appointment_date, appointment_time), timezone=timezone.get_current_timezone())
    min_advance_hours = inventory_settings.min_advance_booking_hours

    earliest_allowed_datetime = now_aware + timedelta(hours=min_advance_hours)
    if appointment_datetime_aware <= earliest_allowed_datetime:
        errors.append(
            f"The selected time is too soon. Appointments require at least {min_advance_hours} hours notice from the current time."
        )

    # Check for overlaps with existing booked times
    for booked_time_obj in existing_booked_times:
        booked_datetime_aware = timezone.make_aware(datetime.combine(appointment_date, booked_time_obj), timezone=timezone.get_current_timezone())
        blocked_interval_start = booked_datetime_aware - timedelta(minutes=spacing_minutes)
        blocked_interval_end = booked_datetime_aware + timedelta(minutes=spacing_minutes)

        if blocked_interval_start <= appointment_datetime_aware <= blocked_interval_end:
            errors.append(f"The selected time ({appointment_time.strftime('%H:%M')}) overlaps with an existing appointment.")
            break # No need to check other booked times if one overlap is found

    return errors
