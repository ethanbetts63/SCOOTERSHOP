# core/views/main.py

from django.shortcuts import render, redirect # Import redirect
from django.conf import settings
from django.contrib import messages # Import messages
import requests
import json
from ..models import ServiceType, SiteSettings # Import models from the parent directory
from .utils import get_featured_motorcycles # Import utility function


# Home Page
def index(request):
    # You might want to get this from SiteSettings
    place_id = 'ChIJy_zrHmGhMioRisz6mis0SpQ' # Ensure this is correct or comes from settings
    # Ensure MAPS_API_KEY is in your project's settings.py
    api_key = settings.MAPS_API_KEY
    all_reviews = []
    five_star_reviews = []

    # Check if Google Places API is enabled in SiteSettings if you add that option
    site_settings = SiteSettings.get_settings()


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
            print(f"API status is not OK or no reviews found in response. Status: {data.get('status')}")

    except requests.exceptions.RequestException as e:
        print(f"Error fetching reviews: {e}")
    except Exception as e:
        print(f"An unexpected error occurred fetching reviews: {e}")


    featured_new_motorcycles = []
    featured_used_motorcycles = []

    # Only fetch featured motorcycles if the section is enabled
    if site_settings.enable_featured_section:
        featured_new_motorcycles = get_featured_motorcycles(condition='new', limit=3)
        featured_used_motorcycles = get_featured_motorcycles(condition='used', limit=3)


    # Pass the filtered 5-star reviews and featured bikes to the template
    context = {
        'reviews': five_star_reviews,
        'featured_new_motorcycles': featured_new_motorcycles,
        'featured_used_motorcycles': featured_used_motorcycles, 
        'maps_api_key': api_key, 
        'place_id': place_id
    }

    return render(request, 'scooter_shop/index.html', context)


# Service Page
def service(request):
    settings = SiteSettings.get_settings()
    # CORRECTED: Check for 'enable_service_booking' which exists on SiteSettings
    if not settings.enable_service_booking:
         messages.error(request, "Service booking is currently disabled.")
         return redirect('index') # Or a dedicated service disabled page

    # Get all active service types
    service_types = ServiceType.objects.filter(is_active=True)
    context = {
        'service_types': service_types
    }
    return render(request, "scooter_shop/service.html", context)