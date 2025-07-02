import datetime
from django.utils import timezone
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages


def set_recent_booking_flag(request):
    request.session["last_sales_booking_timestamp"] = timezone.now().isoformat()


def check_and_manage_recent_booking_flag(request):
    last_booking_timestamp_str = request.session.get("last_sales_booking_timestamp")

    if last_booking_timestamp_str:
        try:
            last_booking_time = timezone.datetime.fromisoformat(
                last_booking_timestamp_str
            )
            cooling_off_period = datetime.timedelta(minutes=2)

            if timezone.now() - last_booking_time < cooling_off_period:
                messages.warning(
                    request,
                    "You recently completed a purchase or reservation. If you wish to make another, please wait a few moments.",
                )
                return redirect(reverse("inventory:used"))
            else:
                del request.session["last_sales_booking_timestamp"]
        except (ValueError, TypeError):
            request.session.pop("last_sales_booking_timestamp", None)

    return None
