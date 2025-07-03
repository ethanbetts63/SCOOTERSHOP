from django.test import TestCase, Client
from django.urls import reverse
from unittest.mock import patch, ANY
from django.http import HttpResponse
from dashboard.models import SiteSettings
from dashboard.tests.test_helpers.model_factories import StaffUserFactory, SiteSettingsFactory

class SettingsBusinessInfoViewTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.staff_user = StaffUserFactory()
        self.site_settings = SiteSettingsFactory()

    @patch('dashboard.views.settings_business_info.render')
    def test_settings_business_info_view_get(self, mock_render):
        mock_render.return_value = HttpResponse()
        self.client.login(username=self.staff_user.username, password='testpassword')
        response = self.client.get(reverse('dashboard:settings_business_info'))
        self.assertEqual(response.status_code, 200)
        mock_render.assert_called_once_with(ANY, 'dashboard/settings_business_info.html', ANY)

    def test_settings_business_info_view_post_valid(self):
        self.client.login(username=self.staff_user.username, password='testpassword')
        form_data = {
            'phone_number': '1111111111',
            'email_address': 'new@example.com',
            'storefront_address': 'New Address',
            'opening_hours_monday': '8-4',
            'opening_hours_tuesday': '8-4',
            'opening_hours_wednesday': '8-4',
            'opening_hours_thursday': '8-4',
            'opening_hours_friday': '8-4',
            'opening_hours_saturday': '9-3',
            'opening_hours_sunday': 'Closed',
            'google_places_place_id': 'new_id',
        }
        response = self.client.post(reverse('dashboard:settings_business_info'), data=form_data)
        self.assertEqual(response.status_code, 302)  # Redirect on success
        updated_settings = SiteSettings.get_settings()
        self.assertEqual(updated_settings.phone_number, '1111111111')

    @patch('dashboard.views.settings_business_info.render')
    def test_settings_business_info_view_post_invalid(self, mock_render):
        mock_render.return_value = HttpResponse()
        self.client.login(username=self.staff_user.username, password='testpassword')
        form_data = {'email_address': 'invalid-email'}  # Invalid data
        response = self.client.post(reverse('dashboard:settings_business_info'), data=form_data)
        self.assertEqual(response.status_code, 200)  # Stays on page with errors
        mock_render.assert_called_once_with(ANY, 'dashboard/settings_business_info.html', ANY)
