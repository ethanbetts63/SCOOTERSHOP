from datetime import timedelta
from inventory.utils.get_sales_appointment_date_info import get_sales_appointment_date_info
from inventory.models import InventorySettings

def has_available_date(inventory_settings: InventorySettings, is_deposit_flow: bool = False) -> bool:
    """
    Checks if there is at least one available date for a sales appointment.

    This function uses get_sales_appointment_date_info to determine the range
    of possible booking dates and a list of all blocked dates (including non-working
    days and manually blocked dates). It then checks if there is at least one
    date within the possible range that is not in the blocked list.

    Args:
        inventory_settings: The InventorySettings object.
        is_deposit_flow: A boolean indicating if the check is for a flow that
                         requires a deposit, which may affect the max booking date.

    Returns:
        True if at least one appointment date is available, False otherwise.
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
            # Found an available date, so we can return True immediately.
            return True
        current_date += timedelta(days=1)

    return False
