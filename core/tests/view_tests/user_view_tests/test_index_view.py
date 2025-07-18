from django.test import TestCase, Client
from django.urls import reverse
from unittest.mock import patch, MagicMock
import requests
from dashboard.models import SiteSettings
from service.models import ServiceSettings
from service.forms import ServiceDetailsForm
from datetime import date


class IndexViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse("core:index")

        self.mock_site_settings = MagicMock(spec=SiteSettings)
        self.mock_site_settings.enable_google_places_reviews = False
        self.mock_site_settings.google_places_place_id = "test_place_id"

        self.mock_service_settings = MagicMock(spec=ServiceSettings)
        self.mock_service_settings.service_booking_enabled = True

        patch_site_settings = patch(
            "dashboard.models.SiteSettings.get_settings",
            return_value=self.mock_site_settings,
        )
        patch_service_settings = patch(
            "service.models.ServiceSettings.objects.first",
            return_value=self.mock_service_settings,
        )

        self.mock_get_settings = patch_site_settings.start()
        self.mock_service_settings_first = patch_service_settings.start()
        self.addCleanup(patch_site_settings.stop)
        self.addCleanup(patch_service_settings.stop)

        self.mock_get_service_date_availability_patch = patch(
            "core.views.user_views.index.get_service_date_availability"
        )
        self.mock_get_service_date_availability = (
            self.mock_get_service_date_availability_patch.start()
        )
        self.mock_get_service_date_availability.return_value = (date.today(), "[]")
        self.addCleanup(self.mock_get_service_date_availability_patch.stop)

    def test_index_view_get(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/index.html")
        self.assertIn("form", response.context)
        self.assertIsInstance(response.context["form"], ServiceDetailsForm)
        self.assertIn("service_settings", response.context)
        self.assertEqual(
            response.context["service_settings"], self.mock_service_settings
        )
        self.assertIn("blocked_service_dates_json", response.context)
        self.assertIn("min_service_date_flatpickr", response.context)
        self.assertIn("temp_service_booking", response.context)
        self.assertIsNone(response.context["temp_service_booking"])
        self.assertIn("reviews", response.context)
        self.assertEqual(response.context["reviews"], [])

    @patch("requests.get")
    def test_index_view_with_google_reviews_enabled(self, mock_requests_get):
        self.mock_site_settings.enable_google_places_reviews = True
        self.mock_site_settings.google_places_place_id = "test_place_id"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "OK",
            "result": {
                "reviews": [
                    {"rating": 5, "text": "Great service!", "time": 1678886400},
                    {"rating": 4, "text": "Good experience", "time": 1678790400},
                    {"rating": 5, "text": "Excellent!", "time": 1678972800},
                ]
            },
        }
        mock_requests_get.return_value = mock_response

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/index.html")
        self.assertIn("reviews", response.context)
        self.assertEqual(len(response.context["reviews"]), 2)

        self.assertEqual(response.context["reviews"][0]["text"], "Excellent!")

    @patch("requests.get")
    def test_index_view_with_google_reviews_api_error(self, mock_requests_get):
        self.mock_site_settings.enable_google_places_reviews = True
        self.mock_site_settings.google_places_place_id = "test_place_id"

        mock_requests_get.side_effect = requests.exceptions.RequestException(
            "API Error"
        )

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/index.html")
        self.assertIn("reviews", response.context)
        self.assertEqual(response.context["reviews"], [])
