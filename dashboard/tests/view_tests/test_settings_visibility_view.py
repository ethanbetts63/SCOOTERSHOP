from django.test import TestCase, Client
from django.urls import reverse
from dashboard.models import SiteSettings
from users.tests.test_helpers.model_factories import (
    StaffUserFactory,
)
from dashboard.tests.test_helpers.model_factories import SiteSettingsFactory

class SettingsVisibilityViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.staff_user = StaffUserFactory()
        self.site_settings = SiteSettingsFactory()

    def test_settings_visibility_view_get(self):
        self.client.login(username=self.staff_user.username, password="password123")
        response = self.client.get(reverse("dashboard:settings_visibility"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "dashboard/settings_visibility.html")

    def test_settings_visibility_view_post_valid(self):
        self.client.login(username=self.staff_user.username, password="password123")
        form_data = {
            "enable_service_booking": False,
            "enable_user_accounts": False,
            "enable_contact_page": False,
            "enable_map_display": False,
            "enable_privacy_policy_page": False,
            "enable_returns_page": False,
            "enable_security_page": False,
            "enable_google_places_reviews": False,
        }
        response = self.client.post(
            reverse("dashboard:settings_visibility"), data=form_data
        )
        self.assertEqual(response.status_code, 302)
        updated_settings = SiteSettings.get_settings()
        self.assertFalse(updated_settings.enable_service_booking)

    def test_settings_visibility_view_post_invalid(self):
        self.client.login(username=self.staff_user.username, password="password123")
        form_data = {
            "enable_service_booking": "not-a-boolean"
        }  
        response = self.client.post(
            reverse("dashboard:settings_visibility"), data=form_data
        )
        self.assertEqual(response.status_code, 302)
        updated_settings = SiteSettings.get_settings()
        self.assertTrue(updated_settings.enable_service_booking)
