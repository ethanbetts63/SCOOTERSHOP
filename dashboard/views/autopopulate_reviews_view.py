import requests
from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse
from django.views import View
from django.contrib import messages
from inventory.mixins import AdminRequiredMixin
from dashboard.models import Review, SiteSettings


class AutopopulateReviewsView(AdminRequiredMixin, View):
    """
    Autopopulates the database with the 5 most recent 5-star reviews from the Google Places API.
    """

    def post(self, request, *args, **kwargs):
        print("AutopopulateReviewsView: POST request received.")
        site_settings = SiteSettings.get_settings()
        api_key = settings.GOOGLE_API_KEY
        place_id = site_settings.google_places_place_id

        if not all([api_key, place_id]):
            messages.error(request, "Google API key or Place ID is not configured.")
            print("AutopopulateReviewsView: API key or Place ID missing.")
            return redirect(reverse("dashboard:reviews_management"))

        url = f"https://maps.googleapis.com/maps/api/place/details/json?place_id={place_id}&fields=name,review&key={api_key}&reviews_sort=newest"
        print(f"AutopopulateReviewsView: Google Places API URL: {url}")

        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            print(
                f"AutopopulateReviewsView: Raw Google API response status: {data.get('status')}"
            )
            print(
                f"AutopopulateReviewsView: Raw Google API response reviews count: {len(data.get('result', {}).get('reviews', []))}"
            )
        except requests.exceptions.RequestException as e:
            messages.error(
                request, f"Failed to fetch reviews from Google Places API: {e}"
            )
            print(f"AutopopulateReviewsView: Error fetching reviews: {e}")
            return redirect(reverse("dashboard:reviews_management"))

        if data.get("status") != "OK":
            messages.error(request, f"Google Places API error: {data.get('status')}")
            print(
                f"AutopopulateReviewsView: Google Places API error status: {data.get('status')}"
            )
            return redirect(reverse("dashboard:reviews_management"))

        reviews = data.get("result", {}).get("reviews", [])
        print(f"AutopopulateReviewsView: Total reviews from API: {len(reviews)}")

        five_star_reviews = [
            r for r in reviews if r.get("rating") == 5 and r.get("text")
        ]
        print(
            f"AutopopulateReviewsView: 5-star reviews with text: {len(five_star_reviews)}"
        )

        new_reviews_count = 0
        for review_data in five_star_reviews[:5]:
            author_name = review_data.get("author_name")
            text = review_data.get("text")
            print(
                f"AutopopulateReviewsView: Processing review by {author_name} (text: {text[:30]}...)"
            )

            if not Review.objects.filter(author_name=author_name, text=text).exists():
                Review.objects.create(
                    author_name=author_name,
                    rating=review_data.get("rating"),
                    text=text,
                    profile_photo_url=review_data.get("profile_photo_url"),
                )
                new_reviews_count += 1
                print(f"AutopopulateReviewsView: Added new review by {author_name}.")
            else:
                print(
                    f"AutopopulateReviewsView: Review by {author_name} already exists, skipping."
                )

        if new_reviews_count > 0:
            messages.success(
                request,
                f"Successfully autopopulated {new_reviews_count} new 5-star reviews.",
            )
            print(
                f"AutopopulateReviewsView: Successfully added {new_reviews_count} reviews."
            )
        else:
            messages.info(request, "No new 5-star reviews to add.")
            print("AutopopulateReviewsView: No new 5-star reviews to add.")

        return redirect(reverse("dashboard:reviews_management"))
