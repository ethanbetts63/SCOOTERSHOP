import requests
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.contrib.auth.decorators import login_required
from dashboard.models import SiteSettings
from ..decorators import admin_required

@require_GET
@admin_required
def search_google_reviews_ajax(request):
    """
    Handles AJAX requests to search for Google reviews based on a query.
    """
    print("AJAX view called")

    search_term = request.GET.get("query", "").strip().lower()
    print(f"Search term: {search_term}")
    
    site_settings = SiteSettings.get_settings()
    api_key = settings.GOOGLE_API_KEY
    place_id = site_settings.google_places_place_id
    print(f"API Key: {api_key}")
    print(f"Place ID: {place_id}")

    if not all([api_key, place_id]):
        print("API key or Place ID not configured")
        return JsonResponse({"error": "Google API key or Place ID is not configured."}, status=500)

    url = f"https://maps.googleapis.com/maps/api/place/details/json?place_id={place_id}&fields=name,review&key={api_key}&reviews_sort=newest"
    print(f"Request URL: {url}")
    
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for bad status codes
        data = response.json()
        print(f"Google Places API response: {data}")
    except requests.exceptions.RequestException as e:
        print(f"Failed to fetch reviews: {e}")
        return JsonResponse({"error": f"Failed to fetch reviews from Google Places API: {e}"}, status=500)

    if data.get("status") != "OK":
        print(f"Google Places API error: {data.get('status')}")
        return JsonResponse({"error": f"Google Places API error: {data.get('status')}"}, status=500)

    reviews = data.get("result", {}).get("reviews", [])
    print(f"Found {len(reviews)} reviews")
    
    filtered_reviews = [
        review for review in reviews 
        if search_term in review.get("author_name", "").lower() or search_term in review.get("text", "").lower()
    ]
    print(f"Found {len(filtered_reviews)} filtered reviews")

    reviews_data = [
        {
            "author_name": review.get("author_name"),
            "rating": review.get("rating"),
            "text": review.get("text"),
            "profile_photo_url": review.get("profile_photo_url"),
        }
        for review in filtered_reviews
    ]

    return JsonResponse({"reviews": reviews_data})
