from django.test import TestCase
from dashboard.forms import BusinessInfoForm


class BusinessInfoFormTest(TestCase):
    def test_valid_form(self):
        form_data = {
            "phone_number": "1234567890",
            "email_address": "test@example.com",
            "street_address": "123 Test St",
            "address_locality": "Test City",
            "address_region": "TS",
            "postal_code": "12345",
            "opening_hours_monday": "9-5",
            "opening_hours_tuesday": "9-5",
            "opening_hours_wednesday": "9-5",
            "opening_hours_thursday": "9-5",
            "opening_hours_friday": "9-5",
            "opening_hours_saturday": "10-4",
            "opening_hours_sunday": "Closed",
            "google_places_place_id": "12345",
        }
        form = BusinessInfoForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_invalid_form(self):
        form_data = {"email_address": "not-an-email"}
        form = BusinessInfoForm(data=form_data)
        self.assertFalse(form.is_valid())
