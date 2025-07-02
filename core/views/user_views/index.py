from django.shortcuts import render
from django.conf import settings
import requests
import sys
from dashboard.models import SiteSettings
from service.models import ServiceSettings, TempServiceBooking
from service.forms import ServiceDetailsForm
from service.utils import get_service_date_availability
from django.views.decorators.http import require_http_methods


@require_http_methods(["GET"])
def index(request):
    site_settings = SiteSettings.get_settings()
    service_settings = ServiceSettings.objects.first()

    place_id = site_settings.google_places_place_id
    api_key = settings.GOOGLE_API_KEY
    is_testing = "test" in sys.argv or "manage.py" in sys.argv
    places_api_url = f"https://maps.googleapis.com/maps/api/place/details/json?place_id={place_id}&fields=reviews&key={api_key}"

    all_reviews = []
    five_star_reviews = []

    if site_settings.enable_google_places_reviews and place_id and api_key:
        try:
            response = requests.get(places_api_url)
            response.raise_for_status()
            data = response.json()

            if (
                data.get("status") == "OK"
                and "result" in data
                and "reviews" in data["result"]
            ):
                all_reviews = data["result"]["reviews"]
                five_star_reviews = [
                    review for review in all_reviews if review.get("rating") == 5
                ]
                five_star_reviews.sort(key=lambda x: x.get("time", 0), reverse=True)
            else:
                pass
        except requests.exceptions.RequestException as e:
            pass
        except Exception as e:
            pass

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

    context = {
        "reviews": five_star_reviews,
        "google_api_key": settings.GOOGLE_API_KEY,
        "form": service_form,
        "service_settings": service_settings,
        "blocked_service_dates_json": disabled_dates_json,
        "min_service_date_flatpickr": min_date_for_flatpickr.strftime("%Y-%m-%d"),
        "temp_service_booking": temp_service_booking,
    }

    return render(request, "core/index.html", context)
