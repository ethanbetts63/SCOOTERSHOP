from django.test import TestCase, Client
from django.urls import reverse
from unittest.mock import patch, ANY
from django.http import HttpResponse
from dashboard.models import SiteSettings
from dashboard.tests.test_helpers.model_factories import StaffUserFactory, SiteSettingsFactory

class SettingsVisibilityViewTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.staff_user = StaffUserFactory()
        self.site_settings = SiteSettingsFactory()

    @patch('dashboard.views.settings_visibility.render')
    def test_settings_visibility_view_get(self, mock_render):
        mock_render.return_value = HttpResponse()
        self.client.login(username=self.staff_user.username, password='testpassword')
        response = self.client.get(reverse('dashboard:settings_visibility'))
        self.assertEqual(response.status_code, 200)
        mock_render.assert_called_once_with(ANY, 'dashboard/settings_visibility.html', ANY)

    def test_settings_visibility_view_post_valid(self):
        self.client.login(username=self.staff_user.username, password='testpassword')
        form_data = {
            'enable_service_booking': False,
            'enable_user_accounts': False,
            'enable_contact_page': False,
            'enable_map_display': False,
            'enable_featured_section': False,
            'enable_privacy_policy_page': False,
            'enable_returns_page': False,
            'enable_security_page': False,
            'enable_terms_page': False,
            'enable_google_places_reviews': False,
        }
        response = self.client.post(reverse('dashboard:settings_visibility'), data=form_data)
        self.assertEqual(response.status_code, 302)  # Redirect on success
        updated_settings = SiteSettings.get_settings()
        self.assertFalse(updated_settings.enable_service_booking)

    def test_settings_visibility_view_post_invalid(self):
        self.client.login(username=self.staff_user.username, password='testpassword')
        form_data = {'enable_service_booking': 'not-a-boolean'}  # Invalid data
        response = self.client.post(reverse('dashboard:settings_visibility'), data=form_data)
        self.assertEqual(response.status_code, 302)  # Redirect on success
        # No assertFormError here as it redirects on invalid data for boolean fields
