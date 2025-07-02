from django.utils import timezone
from datetime import timedelta
from service.models import BlockedServiceDate


def get_drop_off_date_availability(temp_booking, service_settings):

    today = timezone.localdate(timezone.now())
    service_date = temp_booking.service_date
    max_advance_days = service_settings.max_advance_dropoff_days
    allow_after_hours_dropoff = service_settings.allow_after_hours_dropoff
    booking_open_days_str = service_settings.booking_open_days

    day_name_to_weekday_num = {
        "Mon": 0,
        "Tue": 1,
        "Wed": 2,
        "Thu": 3,
        "Fri": 4,
        "Sat": 5,
        "Sun": 6,
    }

    if booking_open_days_str:
        booking_open_weekdays = {
            day_name_to_weekday_num[day.strip()]
            for day in booking_open_days_str.split(",")
            if day.strip() in day_name_to_weekday_num
        }
    else:
        booking_open_weekdays = set()

    calculated_max_dropoff_date = service_date

    calculated_min_dropoff_date = service_date - timedelta(days=max_advance_days)

    if calculated_min_dropoff_date < today:
        calculated_min_dropoff_date = today

    available_dates = []

    if calculated_min_dropoff_date > calculated_max_dropoff_date:
        return []

    blocked_dates = BlockedServiceDate.objects.filter(
        start_date__lte=calculated_max_dropoff_date,
        end_date__gte=calculated_min_dropoff_date,
    ).values_list("start_date", "end_date")

    blocked_date_set = set()
    for start, end in blocked_dates:
        current_blocked_day = start
        while current_blocked_day <= end:
            blocked_date_set.add(current_blocked_day)
            current_blocked_day += timedelta(days=1)

    current_date = calculated_min_dropoff_date
    while current_date <= calculated_max_dropoff_date:

        if current_date not in blocked_date_set:

            if not allow_after_hours_dropoff:
                if current_date.weekday() in booking_open_weekdays:
                    available_dates.append(current_date.strftime("%Y-%m-%d"))
            else:

                available_dates.append(current_date.strftime("%Y-%m-%d"))

        current_date += timedelta(days=1)

    return available_dates
