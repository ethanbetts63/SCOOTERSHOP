# core/views/main.py

from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib import messages
import requests
import json


# Import models from other apps as needed
from dashboard.models import SiteSettings # Import SiteSettings from the dashboard app
from service.models import ServiceType # Assuming ServiceType moved to service app
# Import utility function from the inventory app
from inventory.views.utils import get_featured_motorcycles

# Home Page
def index(request):
    # You might want to get this from SiteSettings
    # Ensure this is correct or comes from settings/SiteSettings
    site_settings = SiteSettings.get_settings()
    place_id = site_settings.google_places_place_id # Assuming this setting exists
    api_key = settings.MAPS_API_KEY # Keep API key in settings.py for security

    all_reviews = []
    five_star_reviews = []

    # Check if Google Places API is enabled in SiteSettings
    if site_settings.enable_google_places_reviews and place_id and api_key: # Assuming this setting exists
        places_api_url = f"https://maps.googleapis.com/maps/api/place/details/json?place_id={place_id}&fields=reviews&key={api_key}"

        try:
            response = requests.get(places_api_url)
            response.raise_for_status()
            data = response.json()

            if data.get('status') == 'OK' and 'result' in data and 'reviews' in data['result']:
                all_reviews = data['result']['reviews']

                # Filter for 5-star reviews
                five_star_reviews = [review for review in all_reviews if review.get('rating') == 5]

                # Sort reviews by time (most recent first)
                # Google Places API provides 'time' as a Unix timestamp
                five_star_reviews.sort(key=lambda x: x.get('time', 0), reverse=True)

            else:
                print(f"Google Places API Error: Status is not OK or no reviews found in response. Status: {data.get('status')}")
                # Optionally add a user-facing message here
                # messages.warning(request, "Could not fetch recent reviews.")

        except requests.exceptions.RequestException as e:
            print(f"Error fetching reviews from Google Places API: {e}")
            # messages.error(request, "There was an error fetching reviews.")
        except Exception as e:
            print(f"An unexpected error occurred fetching reviews: {e}")
            # messages.error(request, "An unexpected error occurred.")


    featured_new_motorcycles = []
    featured_used_motorcycles = []

    # Only fetch featured motorcycles if the section is enabled via SiteSettings
    if site_settings.enable_featured_section: # Assuming this setting exists
        try:
            featured_new_motorcycles = get_featured_motorcycles(condition='new', limit=3)
            featured_used_motorcycles = get_featured_motorcycles(condition='used', limit=3)
        except Exception as e:
            print(f"Error fetching featured motorcycles: {e}")
            # messages.warning(request, "Could not fetch featured motorcycles.")


    # Pass the filtered 5-star reviews and featured bikes to the template
    context = {
        'reviews': five_star_reviews,
        'featured_new_motorcycles': featured_new_motorcycles,
        'featured_used_motorcycles': featured_used_motorcycles,
        # Only pass API key and place ID if reviews are enabled, or handle in template
        'maps_api_key': api_key if site_settings.enable_google_places_reviews else None,
        'place_id': place_id if site_settings.enable_google_places_reviews else None,
    }

    # Updated template path
    return render(request, 'core/scooter_shop/index.html', context)


# General Service Information Page (not booking flow)
# This view remains in core as a static-like information page about services offered.
# The actual booking functionality is in the 'service' app.
def service(request):
    settings = SiteSettings.get_settings()
    # Check if the general service info page is enabled (assuming a new setting or using the booking setting)
    # Let's use the enable_service_booking setting for now, adjust if a dedicated setting is added
    if not settings.enable_service_booking:
         messages.error(request, "Service information is currently disabled.")
         # Updated redirect URL to use the core namespace
         return redirect('core:index')

    # Get all active service types to display on the info page
    try:
        service_types = ServiceType.objects.filter(is_active=True)
    except Exception as e:
        print(f"Error fetching service types for service info page: {e}")
        service_types = [] # Ensure service_types is a list even if fetching fails
        messages.warning(request, "Could not load service types.")


    context = {
        'service_types': service_types
    }
    # Updated template path
    return render(request, "core/scooter_shop/service.html", context)