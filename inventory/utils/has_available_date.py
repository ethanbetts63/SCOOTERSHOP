from datetime import timedelta
from inventory.utils.get_sales_appointment_date_info import get_sales_appointment_date_info
from inventory.models import InventorySettings

def _check_availability(inventory_settings: InventorySettings, is_deposit_flow: bool) -> bool:
    """
    Internal helper function to check for available dates based on flow type.
    """
    if not inventory_settings:
        return False

    min_date, max_date, blocked_dates_str = get_sales_appointment_date_info(
        inventory_settings, is_deposit_flow
    )

    if max_date < min_date:
        return False

    blocked_dates_set = set(blocked_dates_str)
    
    current_date = min_date
    while current_date <= max_date:
        if current_date.strftime("%Y-%m-%d") not in blocked_dates_set:
            return True
        current_date += timedelta(days=1)

    return False

def has_available_date_for_deposit_flow(inventory_settings: InventorySettings) -> bool:
    """
    Checks for available dates specifically for the 'Reserve with Deposit' flow.
    This respects the 'deposit_lifespan_days' setting.
    """
    return _check_availability(inventory_settings, is_deposit_flow=True)

def has_available_date_for_viewing_flow(inventory_settings: InventorySettings) -> bool:
    """
    Checks for available dates for the non-deposit 'Book a viewing' flow.
    This respects the general 'max_advance_booking_days' setting.
    """
    return _check_availability(inventory_settings, is_deposit_flow=False)
