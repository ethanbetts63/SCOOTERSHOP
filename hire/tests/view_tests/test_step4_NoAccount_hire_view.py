# hire/tests/view_tests/test_step4_NoAccount_hire_view.py

import datetime
from decimal import Decimal
from unittest.mock import patch, MagicMock
from uuid import uuid4

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.messages import get_messages
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from hire.models import TempHireBooking, DriverProfile
from hire.forms import Step4NoAccountForm
from hire.tests.test_helpers.model_factories import (
    create_temp_hire_booking,
    create_hire_settings,
    create_motorcycle,
)
from dashboard.models import HireSettings


class NoAccountViewTest(TestCase):
    """
    Tests for the NoAccountView (Step 4 for anonymous users).
    """

    def setUp(self):
        """
        Set up common test data and client.
        """
        self.client = Client()
        self.hire_settings = create_hire_settings(
            hire_pricing_strategy='24_hour_customer_friendly', # Example strategy
            excess_hours_margin=2,
            currency_code='AUD'
        )
        self.motorcycle = create_motorcycle(daily_hire_rate=Decimal('100.00'), hourly_hire_rate=Decimal('20.00'))
        self.temp_booking = create_temp_hire_booking(
            motorcycle=self.motorcycle,
            pickup_date=timezone.now().date() + datetime.timedelta(days=2),
            pickup_time=datetime.time(10, 0),
            return_date=timezone.now().date() + datetime.timedelta(days=4), # 2 full days
            return_time=datetime.time(10, 0),
            booked_daily_rate=self.motorcycle.daily_hire_rate,
            booked_hourly_rate=self.motorcycle.hourly_hire_rate,
        )

        # Set up session for the client
        session = self.client.session
        session["temp_booking_id"] = self.temp_booking.id
        session["temp_booking_uuid"] = str(self.temp_booking.session_uuid)
        session.save()

        self.step4_no_account_url = reverse("hire:step4_no_account")
        self.step2_url = reverse("hire:step2_choose_bike")
        self.step5_url = reverse("hire:step5_summary_payment_options")

        # Dummy file for uploads
        self.dummy_license_photo = SimpleUploadedFile(
            "license.jpg", b"file_content_license", content_type="image/jpeg"
        )
        self.dummy_passport_photo = SimpleUploadedFile(
            "passport.jpg", b"file_content_passport", content_type="image/jpeg"
        )
        self.dummy_int_license_photo = SimpleUploadedFile(
            "int_license.jpg", b"file_content_int_license", content_type="image/jpeg"
        )

        self.valid_australian_data = {
            "name": "Test User",
            "email": "test@example.com",
            "phone_number": "0412345678",
            "address_line_1": "123 Test St",
            "city": "Testville",
            "country": "Australia",
            "date_of_birth": "1990-01-01",
            "is_australian_resident": "True",
            "license_number": "123456789",
            "license_expiry_date": (timezone.now().date() + datetime.timedelta(days=365)).strftime('%Y-%m-%d'),
            # 'license_photo' will be in files
        }
        self.valid_australian_files = {'license_photo': self.dummy_license_photo}

    def test_get_no_account_view_success(self):
        """
        Test GET request for the NoAccountView successfully renders the form.
        """
        response = self.client.get(self.step4_no_account_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "hire/step4_no_account.html")
        self.assertIsInstance(response.context["form"], Step4NoAccountForm)
        self.assertEqual(response.context["temp_booking"], self.temp_booking)
        # Check that the form is initialized with the temp_booking
        self.assertEqual(response.context["form"].temp_booking, self.temp_booking)


    def test_get_no_account_view_session_expired(self):
        """
        Test GET request when temp_booking_id is not in session.
        """
        session = self.client.session
        del session["temp_booking_id"]
        session.save()

        response = self.client.get(self.step4_no_account_url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.step2_url)
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Your booking session has expired. Please start again.")

    def test_get_no_account_view_temp_booking_not_found(self):
        """
        Test GET request when temp_booking_id in session does not match any TempHireBooking.
        """
        session = self.client.session
        session["temp_booking_id"] = 99999  # Non-existent ID
        session.save()

        response = self.client.get(self.step4_no_account_url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.step2_url)
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Your booking session has expired. Please start again.")

    @patch("hire.views.step4_NoAccount_view.calculate_booking_grand_total")
    def test_post_no_account_view_valid_data_australian(self, mock_calculate_grand_total):
        """
        Test POST request with valid data for an Australian resident.
        """
        # Mock the pricing calculation
        mock_calculate_grand_total.return_value = {
            'motorcycle_price': Decimal('200.00'), # 2 days * 100/day
            'package_price': Decimal('0.00'),
            'addons_total_price': Decimal('0.00'),
            'grand_total': Decimal('200.00'),
            'deposit_amount': Decimal('20.00'),
            'currency': 'AUD'
        }

        self.assertEqual(DriverProfile.objects.count(), 0)
        initial_temp_booking_driver_profile = self.temp_booking.driver_profile

        response = self.client.post(self.step4_no_account_url, data=self.valid_australian_data, files=self.valid_australian_files)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.step5_url)

        # Check DriverProfile creation
        self.assertEqual(DriverProfile.objects.count(), 1)
        driver_profile = DriverProfile.objects.first()
        self.assertEqual(driver_profile.name, self.valid_australian_data["name"])
        self.assertEqual(driver_profile.email, self.valid_australian_data["email"])
        self.assertTrue(driver_profile.license_photo.name.endswith('.jpg'))


        # Check TempHireBooking update
        self.temp_booking.refresh_from_db()
        self.assertNotEqual(initial_temp_booking_driver_profile, self.temp_booking.driver_profile)
        self.assertEqual(self.temp_booking.driver_profile, driver_profile)

        # Check pricing fields update
        mock_calculate_grand_total.assert_called_once_with(self.temp_booking, self.hire_settings)
        self.assertEqual(self.temp_booking.total_hire_price, Decimal('200.00'))
        self.assertEqual(self.temp_booking.total_package_price, Decimal('0.00'))
        self.assertEqual(self.temp_booking.total_addons_price, Decimal('0.00'))
        self.assertEqual(self.temp_booking.grand_total, Decimal('200.00'))
        # Deposit amount is not set by this view directly based on calculate_booking_grand_total in current implementation
        # but it might be if the function returned it and view used it. For now, it's None or its previous value.
        # self.assertEqual(self.temp_booking.deposit_amount, Decimal('20.00')) # Assuming calculate_booking_grand_total sets it

        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Driver details saved successfully.")

    def test_post_no_account_view_invalid_data(self):
        """
        Test POST request with invalid data.
        """
        invalid_data = self.valid_australian_data.copy()
        invalid_data["email"] = "not-an-email"  # Invalid email

        response = self.client.post(self.step4_no_account_url, data=invalid_data, files=self.valid_australian_files)

        self.assertEqual(response.status_code, 200) # Should re-render the form
        self.assertTemplateUsed(response, "hire/step4_no_account.html")
        self.assertIsInstance(response.context["form"], Step4NoAccountForm)
        self.assertTrue(response.context["form"].errors)
        self.assertIn("email", response.context["form"].errors)

        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Please correct the errors below.")

        # Ensure no DriverProfile was created
        self.assertEqual(DriverProfile.objects.count(), 0)
        self.temp_booking.refresh_from_db()
        self.assertIsNone(self.temp_booking.driver_profile) # Assuming it was None initially or remains unchanged

    def test_post_no_account_view_session_expired(self):
        """
        Test POST request when temp_booking_id is not in session.
        """
        session = self.client.session
        del session["temp_booking_id"]
        session.save()

        response = self.client.post(self.step4_no_account_url, data=self.valid_australian_data, files=self.valid_australian_files)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.step2_url)
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Your booking session has expired. Please start again.")

    @patch("hire.views.step4_NoAccount_view.calculate_booking_grand_total")
    def test_post_no_account_view_hire_settings_not_found(self, mock_calculate_grand_total):
        """
        Test POST request when HireSettings are not found.
        Pricing should not be updated, but driver profile should still be saved.
        """
        HireSettings.objects.all().delete() # Remove hire settings

        self.assertEqual(DriverProfile.objects.count(), 0)

        response = self.client.post(self.step4_no_account_url, data=self.valid_australian_data, files=self.valid_australian_files)

        self.assertEqual(response.status_code, 302) # Should still redirect
        self.assertRedirects(response, self.step5_url)

        # Driver profile should still be created and linked
        self.assertEqual(DriverProfile.objects.count(), 1)
        driver_profile = DriverProfile.objects.first()
        self.temp_booking.refresh_from_db()
        self.assertEqual(self.temp_booking.driver_profile, driver_profile)

        # Pricing calculation should not have been called effectively or prices remain None/default
        mock_calculate_grand_total.assert_not_called() # Because hire_settings is None
        self.assertIsNone(self.temp_booking.total_hire_price) # Or its initial value if it had one
        self.assertEqual(self.temp_booking.grand_total, None) # Or its initial value

        messages = list(get_messages(response.wsgi_request))
        # Two messages: one warning about settings, one success for driver details
        self.assertTrue(any("Hire settings not found." in str(m) for m in messages))
        self.assertTrue(any("Driver details saved successfully." in str(m) for m in messages))

    def test_post_no_account_foreign_resident_valid(self):
        """
        Test POST request with valid data for a foreign resident.
        This primarily ensures the form validation (tested elsewhere) integrates correctly.
        """
        valid_foreign_data = {
            "name": "Foreign User",
            "email": "foreign@example.com",
            "phone_number": "1234567890",
            "address_line_1": "1 International Drive",
            "city": "Global City",
            "country": "USA",
            "date_of_birth": "1985-03-15",
            "is_australian_resident": "False",
            "international_license_issuing_country": "USA",
            "international_license_expiry_date": (timezone.now().date() + datetime.timedelta(days=365)).strftime('%Y-%m-%d'),
            "passport_number": "P12345USA",
            "passport_expiry_date": (timezone.now().date() + datetime.timedelta(days=365)).strftime('%Y-%m-%d'),
        }
        valid_foreign_files = {
            'international_license_photo': self.dummy_int_license_photo,
            'passport_photo': self.dummy_passport_photo,
        }

        with patch("hire.views.step4_NoAccount_view.calculate_booking_grand_total") as mock_calc:
            mock_calc.return_value = {
                'motorcycle_price': Decimal('200.00'), 'package_price': Decimal('0.00'),
                'addons_total_price': Decimal('0.00'), 'grand_total': Decimal('200.00'),
                'deposit_amount': Decimal('20.00'), 'currency': 'AUD'
            }
            response = self.client.post(self.step4_no_account_url, data=valid_foreign_data, files=valid_foreign_files)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.step5_url)
        self.assertEqual(DriverProfile.objects.count(), 1)
        driver_profile = DriverProfile.objects.first()
        self.assertEqual(driver_profile.name, "Foreign User")
        self.assertFalse(driver_profile.is_australian_resident)
        self.assertTrue(driver_profile.international_license_photo.name.endswith('.jpg'))
        self.assertTrue(driver_profile.passport_photo.name.endswith('.jpg'))

        self.temp_booking.refresh_from_db()
        self.assertEqual(self.temp_booking.driver_profile, driver_profile)
        self.assertEqual(self.temp_booking.grand_total, Decimal('200.00'))


    def tearDown(self):
        """
        Clean up any created files.
        """
        if self.dummy_license_photo:
            # In a real scenario with actual file storage, you might need to delete them.
            # For SimpleUploadedFile, this is usually not necessary as they are in-memory.
            pass
        if DriverProfile.objects.exists():
            for dp in DriverProfile.objects.all():
                if dp.license_photo:
                    dp.license_photo.delete(save=False)
                if dp.international_license_photo:
                    dp.international_license_photo.delete(save=False)
                if dp.passport_photo:
                    dp.passport_photo.delete(save=False)
        # Delete all HireSettings to ensure clean state for other test classes if run together
        # HireSettings.objects.all().delete() # Be cautious if other tests rely on it persisting
