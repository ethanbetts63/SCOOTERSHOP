# core/views/main.py

from django.shortcuts import render
from django.conf import settings
import requests
import sys

# Import models from other apps as needed
from dashboard.models import SiteSettings
# Assuming you have a model for ServiceType in dashboard.models or another app

# Import the utility function for featured motorcycles if still needed
from inventory.views.utils import get_featured_motorcycles


# Home Page
def index(request):
    site_settings = SiteSettings.get_settings()
    place_id = site_settings.google_places_place_id
    api_key = settings.GOOGLE_API_KEY
    is_testing = 'test' in sys.argv or 'manage.py' in sys.argv
    places_api_url = f"https://maps.googleapis.com/maps/api/place/details/json?place_id={place_id}&fields=reviews&key={api_key}"

    all_reviews = []
    five_star_reviews = []

    # Check if Google Places API is enabled in SiteSettings
    if site_settings.enable_google_places_reviews and place_id and api_key: # Assuming this setting exists
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
                # Only print the error if not in a test environment
                if not is_testing:
                    print(f"Google Places API Error: Status is not OK or no reviews found in response. Status: {data.get('status')}")

        except requests.exceptions.RequestException as e:
            # Only print the error if not in a test environment
            if not is_testing:
                print(f"Error fetching reviews from Google Places API: {e}")
        except Exception as e:
            # Only print the error if not in a test environment
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

    # Pass the filtered 5-star reviews and featured bikes to the template
    context = {
        'reviews': five_star_reviews,
        'featured_new_motorcycles': featured_new_motorcycles,
        'featured_used_motorcycles': featured_used_motorcycles,
        'google_api_key': settings.GOOGLE_API_KEY,
    }

    # Updated template path
    return render(request, 'core/index.html', context)