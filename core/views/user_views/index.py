from django.shortcuts import render
from django.conf import settings
from django.views.decorators.http import require_http_methods
from service.models import ServiceSettings, TempServiceBooking
from service.forms import ServiceDetailsForm
from service.utils import get_service_date_availability
from inventory.utils import get_featured_motorcycles
from dashboard.utils import get_reviews  # Import the new utility function

@require_http_methods(["GET"])
def index(request):
    service_settings = ServiceSettings.objects.first()
    service_form = ServiceDetailsForm()
    temp_service_booking = None
    temp_service_booking_uuid = request.session.get("temp_booking_uuid")

    if temp_service_booking_uuid:
        try:
            temp_service_booking = TempServiceBooking.objects.get(
                session_uuid=temp_service_booking_uuid
            )
            service_form = ServiceDetailsForm(
                initial={
                    "service_type": temp_service_booking.service_type,
                    "service_date": temp_service_booking.service_date,
                }
            )
        except TempServiceBooking.DoesNotExist:
            if "temp_booking_uuid" in request.session:
                del request.session["temp_booking_uuid"]
            temp_service_booking = None

    min_date_for_flatpickr, disabled_dates_json = get_service_date_availability()

    featured_new_items = get_featured_motorcycles("new")
    featured_used_items = get_featured_motorcycles("used")
    reviews = get_reviews()  
    context = {
        "reviews": reviews,
        "form": service_form,
        "service_settings": service_settings,
        "blocked_service_dates_json": disabled_dates_json,
        "min_service_date_flatpickr": min_date_for_flatpickr.strftime("%Y-%m-%d"),
        "temp_service_booking": temp_service_booking,
        "featured_new_items": featured_new_items,
        "featured_used_items": featured_used_items,
        "google_api_key": settings.GOOGLE_API_KEY, # Retained for the map include
    }

    return render(request, "core/index.html", context)
