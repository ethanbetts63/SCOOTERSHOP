from django.test import TestCase
from dashboard.forms import VisibilitySettingsForm


class VisibilitySettingsFormTest(TestCase):
    def test_valid_form(self):
        form_data = {
            "enable_service_booking": True,
            "enable_user_accounts": True,
            "enable_contact_page": True,
            "enable_map_display": True,
            "enable_privacy_policy_page": True,
            "enable_returns_page": True,
            "enable_security_page": True,
            "enable_google_places_reviews": True,
        }
        form = VisibilitySettingsForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_invalid_form(self):
        form = VisibilitySettingsForm(data={})
        self.assertTrue(form.is_valid())
