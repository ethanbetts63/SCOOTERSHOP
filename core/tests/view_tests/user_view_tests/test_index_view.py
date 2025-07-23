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
        self.assertQuerySetEqual(response.context["reviews"], [])

    

  