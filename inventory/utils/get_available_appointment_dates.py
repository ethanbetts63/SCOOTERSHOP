from datetime import date, timedelta
from inventory.utils.validate_appointment_date import validate_appointment_date

def get_available_appointment_dates(inventory_settings, is_deposit_flow: bool = False):
    available_dates = []

    if not inventory_settings:
        return available_dates

    general_latest_possible_date = date.today() + timedelta(days=inventory_settings.max_advance_booking_days)

    effective_latest_possible_date = general_latest_possible_date

    if is_deposit_flow:
        deposit_expiry_date = date.today() + timedelta(days=inventory_settings.deposit_lifespan_days)
        effective_latest_possible_date = min(general_latest_possible_date, deposit_expiry_date)

    current_date_iterator = date.today()
    while current_date_iterator <= effective_latest_possible_date:
        date_validation_errors = validate_appointment_date(current_date_iterator, inventory_settings)

        if not date_validation_errors:
            available_dates.append(current_date_iterator)
        
        current_date_iterator += timedelta(days=1)

    return available_dates
