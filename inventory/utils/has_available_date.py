from datetime import timedelta
from inventory.utils.get_sales_appointment_date_info import get_sales_appointment_date_info
from inventory.models import InventorySettings

def has_available_date(inventory_settings: InventorySettings, is_deposit_flow: bool = False) -> bool:
    """
    Checks if there is at least one available date for a sales appointment.
    """
    if not inventory_settings:
        print("--- DEBUG (has_available_date): No inventory_settings provided. ---")
        return False

    min_date, max_date, blocked_dates_str = get_sales_appointment_date_info(
        inventory_settings, is_deposit_flow
    )

    # --- DEBUG PRINT STATEMENTS ---
    print("\n--- DEBUG (has_available_date): STARTING CHECK ---")
    print(f"Calculated Min Date: {min_date}")
    print(f"Calculated Max Date: {max_date}")
    print(f"Total Blocked Dates Found: {len(blocked_dates_str)}")
    print(f"Blocked Dates List: {blocked_dates_str}")
    # --- END DEBUG ---

    if max_date < min_date:
        print("--- DEBUG (has_available_date): Max date is before min date. Returning False. ---")
        return False

    blocked_dates_set = set(blocked_dates_str)
    
    current_date = min_date
    while current_date <= max_date:
        date_str_to_check = current_date.strftime("%Y-%m-%d")
        
        if date_str_to_check not in blocked_dates_set:
            # --- DEBUG PRINT STATEMENT ---
            print(f"--- !!! DEBUG: FOUND AVAILABLE DATE: {date_str_to_check}. Returning True. !!! ---")
            # --- END DEBUG ---
            return True
            
        current_date += timedelta(days=1)

    # --- DEBUG PRINT STATEMENT ---
    print("--- DEBUG (has_available_date): Loop finished. No available dates found. Returning False. ---")
    # --- END DEBUG ---
    return False
