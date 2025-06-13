# inventory/utils/validate_appointment_date.py

from datetime import date, datetime, timedelta
from inventory.models import BlockedSalesDate # Import BlockedSalesDate

def validate_appointment_date(appointment_date: date, inventory_settings):
    errors = []

    if not inventory_settings:
        return errors

    now = datetime.now()

    min_advance_hours = inventory_settings.min_advance_booking_hours
    earliest_allowed_datetime = now + timedelta(hours=min_advance_hours)
    earliest_allowed_date = earliest_allowed_datetime.date()

    if appointment_date < earliest_allowed_date:
        errors.append(f"Appointments must be booked at least {min_advance_hours} hours in advance from now, meaning from {earliest_allowed_date.strftime('%Y-%m-%d')}.")

    max_advance_days = inventory_settings.max_advance_booking_days
    max_booking_date = date.today() + timedelta(days=max_advance_days)
    if appointment_date > max_booking_date:
        errors.append(
            f"Appointments cannot be booked more than {max_advance_days} days in advance (up to {max_booking_date.strftime('%Y-%m-%d')})."
        )

    open_days_str = inventory_settings.sales_booking_open_days
    open_days_map = {
        'Mon': 0, 'Tue': 1, 'Wed': 2, 'Thu': 3, 'Fri': 4, 'Sat': 5, 'Sun': 6
    }
    allowed_weekdays = {open_days_map[d.strip()] for d in open_days_str.split(',') if d.strip() in open_days_map}

    if appointment_date.weekday() not in allowed_weekdays:
        errors.append(
            "Appointments are not available on the selected day of the week."
        )
        
    if BlockedSalesDate.objects.filter(
        start_date__lte=appointment_date,
        end_date__gte=appointment_date
    ).exists():
        errors.append("The selected date is blocked for appointments.")

    return errors
