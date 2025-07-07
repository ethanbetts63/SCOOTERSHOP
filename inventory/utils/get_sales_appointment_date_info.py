from datetime import date, datetime, timedelta
from django.utils import timezone
from inventory.models import InventorySettings, BlockedSalesDate


def get_sales_appointment_date_info(
    inventory_settings: InventorySettings, is_deposit_flow: bool = False
):

    if not inventory_settings:
        # Fallback for when settings are not configured
        return timezone.localdate(), timezone.localdate() + timedelta(days=90), []

    now = timezone.now()

    min_advance_hours = inventory_settings.min_advance_booking_hours
    earliest_allowed_datetime = now + timedelta(hours=min_advance_hours)
    min_date = earliest_allowed_datetime.date()

    # If the last possible appointment on the calculated min_date is earlier than
    # the earliest allowed time, it means no slots are available for that entire day.
    # In this case, we should push the minimum bookable date to the next day.
    if inventory_settings.sales_appointment_end_time:
        end_time_on_min_date = timezone.make_aware(
            datetime.combine(min_date, inventory_settings.sales_appointment_end_time),
            timezone.get_current_timezone(),
        )
        if end_time_on_min_date < earliest_allowed_datetime:
            min_date += timedelta(days=1)

    general_max_date = now.date() + timedelta(
        days=inventory_settings.max_advance_booking_days
    )
    max_date = general_max_date

    if is_deposit_flow and inventory_settings.deposit_lifespan_days is not None:
        deposit_expiry_date = now.date() + timedelta(
            days=inventory_settings.deposit_lifespan_days
        )
        max_date = min(general_max_date, deposit_expiry_date)

    if max_date < min_date:
        max_date = min_date

    blocked_dates = []

    blocked_sales_date_objects = BlockedSalesDate.objects.filter(
        start_date__lte=max_date, end_date__gte=min_date
    )
    for block in blocked_sales_date_objects:
        current_block_date = block.start_date
        while current_block_date <= block.end_date:
            if min_date <= current_block_date <= max_date:
                blocked_dates.append(current_block_date.strftime("%Y-%m-%d"))
            current_block_date += timedelta(days=1)

    open_days_str = inventory_settings.sales_booking_open_days
    open_days_map = {
        "Mon": 0, "Tue": 1, "Wed": 2, "Thu": 3, "Fri": 4, "Sat": 5, "Sun": 6
    }
    allowed_weekdays_indices = {
        open_days_map[d.strip()]
        for d in open_days_str.split(",")
        if d.strip() in open_days_map
    }

    current_date_iterator = min_date
    while current_date_iterator <= max_date:
        if current_date_iterator.weekday() not in allowed_weekdays_indices:
            blocked_dates.append(current_date_iterator.strftime("%Y-%m-%d"))
        current_date_iterator += timedelta(days=1)

    blocked_dates = sorted(list(set(blocked_dates)))

    return min_date, max_date, blocked_dates
