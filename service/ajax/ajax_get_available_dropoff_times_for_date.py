import datetime
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from service.utils.get_available_service_dropoff_times import (
    get_available_dropoff_times,
)
from service.models import TempServiceBooking


@require_GET
def get_available_dropoff_times_for_date(request):
    selected_date_str = request.GET.get("date")

    if not selected_date_str:
        return JsonResponse({"error": "Date parameter is missing."}, status=400)

    try:
        selected_date = datetime.datetime.strptime(selected_date_str, "%Y-%m-%d").date()
    except ValueError:
        return JsonResponse(
            {"error": "Invalid date format. Use YYYY-MM-DD."}, status=400
        )

    temp_service_booking_uuid = request.session.get("temp_service_booking_uuid")
    if not temp_service_booking_uuid:
        return JsonResponse({"error": "Your booking session has expired. Please start over."}, status=400)

    try:
        temp_booking = TempServiceBooking.objects.get(session_uuid=temp_service_booking_uuid)
    except TempServiceBooking.DoesNotExist:
        return JsonResponse({"error": "Your booking session could not be found. Please start over."}, status=400)

    is_service_date = selected_date == temp_booking.service_date

    available_times = get_available_dropoff_times(selected_date, is_service_date)

    formatted_times = [
        {"value": time_str, "text": time_str} for time_str in available_times
    ]

    return JsonResponse({"available_times": formatted_times})
