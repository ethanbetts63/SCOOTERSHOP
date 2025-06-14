# inventory/utils/get_sales_appointment_date_info.py

from datetime import date, datetime, timedelta
from inventory.models import InventorySettings, BlockedSalesDate

def get_sales_appointment_date_info(inventory_settings: InventorySettings, is_deposit_flow: bool = False):
    """
    Calculates and returns the minimum allowed date, maximum allowed date,
    and a list of blocked dates for sales appointments based on InventorySettings
    and BlockedSalesDate entries.

    Args:
        inventory_settings: An instance of InventorySettings model.
        is_deposit_flow: Boolean indicating if the current flow requires a deposit,
                         which might affect the maximum booking date based on deposit lifespan.

    Returns:
        A tuple containing:
        - min_date: The earliest date a booking can be made (date object).
        - max_date: The latest date a booking can be made (date object).
        - blocked_dates: A list of strings (YYYY-MM-DD) for dates that should be
                         disabled in the date picker.
    """
    if not inventory_settings:
        # Return default values if settings are not available
        return date.today(), date.today() + timedelta(days=90), []

    now = datetime.now()

    # 1. Calculate Minimum Allowed Date (based on min_advance_booking_hours)
    min_advance_hours = inventory_settings.min_advance_booking_hours
    earliest_allowed_datetime = now + timedelta(hours=min_advance_hours)
    min_date = earliest_allowed_datetime.date()

    # 2. Calculate Maximum Allowed Date (based on max_advance_booking_days and deposit lifespan)
    general_max_date = date.today() + timedelta(days=inventory_settings.max_advance_booking_days)
    max_date = general_max_date

    # APPLY NEW RULE: If it's a deposit flow, cap the max_date by deposit_lifespan_days
    if is_deposit_flow and inventory_settings.deposit_lifespan_days is not None:
        deposit_expiry_date = date.today() + timedelta(days=inventory_settings.deposit_lifespan_days)
        max_date = min(general_max_date, deposit_expiry_date) # Use the earlier of the two dates

    # Ensure max_date is not earlier than min_date
    if max_date < min_date:
        max_date = min_date # Cap max_date to min_date if settings make it earlier

    # 3. Determine Blocked Dates
    blocked_dates = []

    # Get blocked dates from BlockedSalesDate model
    # Only query for blocked dates within the determined min/max range for efficiency
    blocked_sales_date_objects = BlockedSalesDate.objects.filter(
        start_date__lte=max_date, # Block starts before or on max_date
        end_date__gte=min_date    # Block ends after or on min_date
    )
    for block in blocked_sales_date_objects:
        # Iterate through each day of the block and add to blocked_dates if it's within our valid range
        current_block_date = block.start_date
        while current_block_date <= block.end_date:
            if min_date <= current_block_date <= max_date: # Only block dates within our min/max range
                blocked_dates.append(current_block_date.strftime('%Y-%m-%d'))
            current_block_date += timedelta(days=1)

    # Determine days of the week that are NOT open for sales bookings
    open_days_str = inventory_settings.sales_booking_open_days
    open_days_map = {
        'Mon': 0, 'Tue': 1, 'Wed': 2, 'Thu': 3, 'Fri': 4, 'Sat': 5, 'Sun': 6
    }
    allowed_weekdays_indices = {open_days_map[d.strip()] for d in open_days_str.split(',') if d.strip() in open_days_map}

    # Iterate through the range of dates and add non-open days to blocked_dates
    current_date_iterator = min_date
    while current_date_iterator <= max_date:
        if current_date_iterator.weekday() not in allowed_weekdays_indices:
            blocked_dates.append(current_date_iterator.strftime('%Y-%m-%d'))
        current_date_iterator += timedelta(days=1)

    # Sort and remove duplicates from blocked_dates (important for Flatpickr's disable array)
    blocked_dates = sorted(list(set(blocked_dates)))

    return min_date, max_date, blocked_dates
