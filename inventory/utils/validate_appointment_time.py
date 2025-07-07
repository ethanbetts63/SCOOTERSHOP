from datetime import date, datetime, time, timedelta
from django.utils import timezone


def validate_appointment_time(
    appointment_date: date,
    appointment_time: time,
    inventory_settings,
    existing_booked_times: list,
):
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

    appointment_datetime_aware = timezone.make_aware(
        datetime.combine(appointment_date, appointment_time),
        timezone=timezone.get_current_timezone(),
    )

    for booked_time_obj in existing_booked_times:
        booked_datetime_aware = timezone.make_aware(
            datetime.combine(appointment_date, booked_time_obj),
            timezone=timezone.get_current_timezone(),
        )
        blocked_interval_start = booked_datetime_aware - timedelta(
            minutes=spacing_minutes
        )
        blocked_interval_end = booked_datetime_aware + timedelta(
            minutes=spacing_minutes
        )

        if blocked_interval_start <= appointment_datetime_aware <= blocked_interval_end:
            errors.append(
                f"The selected time ({appointment_time.strftime('%H:%M')}) overlaps with an existing appointment."
            )
            break

    return errors
