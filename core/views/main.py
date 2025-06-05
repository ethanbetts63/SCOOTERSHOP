# core/views/main.py

from django.shortcuts import render
from django.conf import settings
import requests
import sys
import json # Import json for serializing blocked dates

# Import models from other apps as needed
from dashboard.models import SiteSettings, HireSettings
from service.models import ServiceSettings, BlockedServiceDate, TempServiceBooking # Import Service related models
from service.forms import ServiceDetailsForm # Import the ServiceDetailsForm

# Import the utility function for featured motorcycles if still needed
from inventory.views.utils import get_featured_motorcycles

# Import TempHireBooking for potential pre-population of step1 form
from hire.models import TempHireBooking

# Import your new service date availability utility function
from service.utils import get_service_date_availability


# Home Page
def index(request):
    site_settings = SiteSettings.get_settings()
    hire_settings = HireSettings.objects.first() # Get HireSettings for step1_date_time_include
    service_settings = ServiceSettings.objects.first() # Get ServiceSettings for step1_service_details_include

    place_id = site_settings.google_places_place_id
    api_key = settings.GOOGLE_API_KEY
    is_testing = 'test' in sys.argv or 'manage.py' in sys.argv
    places_api_url = f"https://maps.googleapis.com/maps/api/place/details/json?place_id={place_id}&fields=reviews&key={api_key}"

    all_reviews = []
    five_star_reviews = []

    # Check if Google Places API is enabled in SiteSettings
    if site_settings.enable_google_places_reviews and place_id and api_key:
        try:
            response = requests.get(places_api_url)
            response.raise_for_status()
            data = response.json()

            if data.get('status') == 'OK' and 'result' in data and 'reviews' in data['result']:
                all_reviews = data['result']['reviews']
                five_star_reviews = [review for review in all_reviews if review.get('rating') == 5]
                five_star_reviews.sort(key=lambda x: x.get('time', 0), reverse=True)
            else:
                if not is_testing:
                    print(f"Google Places API Error: Status is not OK or no reviews found in response. Status: {data.get('status')}")
        except requests.exceptions.RequestException as e:
            if not is_testing:
                print(f"Error fetching reviews from Google Places API: {e}")
        except Exception as e:
            if not is_testing:
                print(f"An unexpected error occurred fetching reviews: {e}")

    featured_new_motorcycles = []
    featured_used_motorcycles = []

    # Only fetch featured motorcycles if the section is enabled via SiteSettings
    if site_settings.enable_featured_section:
        try:
            featured_new_motorcycles = get_featured_motorcycles(condition='new', limit=3)
            featured_used_motorcycles = get_featured_motorcycles(condition='used', limit=3)
        except Exception as e:
            print(f"Error fetching featured motorcycles: {e}")

    # Try to get TempHireBooking from session for pre-populating Step 1 form
    temp_hire_booking = None
    temp_hire_booking_id = request.session.get('temp_booking_id')
    temp_hire_booking_uuid = request.session.get('temp_booking_uuid')

    if temp_hire_booking_id and temp_hire_booking_uuid:
        try:
            temp_hire_booking = TempHireBooking.objects.get(id=temp_hire_booking_id, session_uuid=temp_hire_booking_uuid)
        except TempHireBooking.DoesNotExist:
            if 'temp_booking_id' in request.session:
                del request.session['temp_booking_id']
            if 'temp_booking_uuid' in request.session:
                del request.session['temp_booking_uuid']
            temp_hire_booking = None

    # --- New: Context for Service Booking Step 1 Form ---
    # Instantiate the ServiceDetailsForm
    service_form = ServiceDetailsForm()

    # Get TempServiceBooking from session for pre-populating service Step 1 form
    temp_service_booking = None
    temp_service_booking_uuid = request.session.get('temp_booking_uuid')

    if temp_service_booking_uuid:
        try:
            temp_service_booking = TempServiceBooking.objects.get(session_uuid=temp_service_booking_uuid)
            # If found, pre-populate the form with its data
            service_form = ServiceDetailsForm(initial={
                'service_type': temp_service_booking.service_type,
                'dropoff_date': temp_service_booking.dropoff_date,
                'dropoff_time': temp_service_booking.dropoff_time,
            })
        except TempServiceBooking.DoesNotExist:
            # If temp booking doesn't exist, clear session key
            if 'temp_booking_uuid' in request.session:
                del request.session['temp_booking_uuid']
            temp_service_booking = None

    # Call the new utility function to get min_date and disabled_dates_json
    min_date_for_flatpickr, disabled_dates_json = get_service_date_availability()

    # Pass the filtered 5-star reviews and featured bikes to the template
    context = {
        'reviews': five_star_reviews,
        'featured_new_motorcycles': featured_new_motorcycles,
        'featured_used_motorcycles': featured_used_motorcycles,
        'google_api_key': settings.GOOGLE_API_KEY,
        'hire_settings': hire_settings, # Pass hire settings for the hire include
        'temp_booking': temp_hire_booking, # Pass temp_booking for pre-populating the hire form

        # New context for service booking Step 1
        'form': service_form, # The ServiceDetailsForm instance
        'service_settings': service_settings, # Pass service settings for the service include
        'blocked_service_dates_json': disabled_dates_json, # Blocked dates for service from utility
        'min_service_date_flatpickr': min_date_for_flatpickr.strftime('%Y-%m-%d'), # Pass min date for Flatpickr
        'temp_service_booking': temp_service_booking, # Pass temp_service_booking for pre-populating service form
    }

    # Updated template path
    return render(request, 'core/index.html', context)
