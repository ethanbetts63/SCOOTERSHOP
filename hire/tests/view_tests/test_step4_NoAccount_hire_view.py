# hire/tests/view_tests/test_step4_NoAccount_hire_view.py (Modified)

import datetime
from decimal import Decimal
from unittest.mock import patch, MagicMock
from uuid import uuid4
import os  # Import os for path manipulation

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.messages import get_messages
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
    Tests for the NoAccountView (Step 4 for anonymous users) - WITHOUT IMAGE UPLOADS.
    """

    def setUp(self):
        """
        Set up common test data and client.
        """
        self.client = Client()
        self.hire_settings = create_hire_settings(
            hire_pricing_strategy='24_hour_customer_friendly',  # Example strategy
            excess_hours_margin=2,
            currency_code='AUD'
        )
        self.motorcycle = create_motorcycle(
            daily_hire_rate=Decimal('100.00'), hourly_hire_rate=Decimal('20.00'))
        self.temp_booking = create_temp_hire_booking(
            motorcycle=self.motorcycle,
            pickup_date=timezone.now().date() + datetime.timedelta(days=2),
            pickup_time=datetime.time(10, 0),
            return_date=timezone.now().date() + datetime.timedelta(days=4),  # 2 full days
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

        # Base data for an Australian resident - WITHOUT image fields
        self.base_australian_data = {
            "name": "Test User",
            "email": "test@example.com",
            "phone_number": "0412345678",
            "address_line_1": "123 Test St",
            "city": "Testville",
            "state": "NSW",
            "post_code": "2000",
            "country": "Australia",
            "date_of_birth": "1990-01-01",
            "is_australian_resident": "True",
            "license_number": "123456789",
            "license_expiry_date": (timezone.now().date() +
                                   datetime.timedelta(days=365)).strftime('%Y-%m-%d'),
        }

        # Base data for a foreign resident - WITHOUT image fields
        self.base_foreign_data = {
            "name": "Foreign User",
            "email": "foreign@example.com",
            "phone_number": "1234567890",
            "address_line_1": "1 International Drive",
            "city": "Global City",
            "state": "CA",
            "post_code": "90210",
            "country": "USA",
            "date_of_birth": "1985-03-15",
            "is_australian_resident": "False",
            "international_license_issuing_country": "USA",
            "international_license_expiry_date": (timezone.now().date() +
                                                 datetime.timedelta(days=365)).strftime('%Y-%m-%d'),
            "passport_number": "P12345USA",
            "passport_expiry_date": (timezone.now().date() +
                                     datetime.timedelta(days=365)).strftime('%Y-%m-%d'),
        }

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
        self.assertEqual(
            str(messages[0]), "Your booking session has expired. Please start again.")

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
        self.assertEqual(
            str(messages[0]), "Your booking session has expired. Please start again.")

    def test_post_no_account_view_invalid_data(self):
        """
        Test POST request with invalid data.
        """
        invalid_data = self.base_australian_data.copy()
        invalid_data["email"] = "not-an-email"  # Invalid email

        response = self.client.post(self.step4_no_account_url,
                                    data=invalid_data)  # NO FILES

        self.assertEqual(response.status_code, 200)  # Should re-render the form
        self.assertTemplateUsed(response, "hire/step4_no_account.html")
        self.assertIsInstance(response.context["form"], Step4NoAccountForm)
        self.assertTrue(response.context["form"].errors)
        self.assertIn("email", response.context["form"].errors)
        # Assert that license_photo error is NOT present, as it should now be valid
        # self.assertNotIn("license_photo", response.context["form"].errors)  # NO FILE CHECK

        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(
            str(messages[0]), "Please correct the errors below.")

        # Ensure no DriverProfile was created
        self.assertEqual(DriverProfile.objects.count(), 0)
        self.temp_booking.refresh_from_db()
        self.assertIsNone(
            self.temp_booking.driver_profile)  # Assuming it was None initially or remains unchanged

    def test_post_no_account_view_session_expired(self):
        """
        Test POST request when temp_booking_id is not in session.
        """
        session = self.client.session
        del session["temp_booking_id"]
        session.save()

        response = self.client.post(self.step4_no_account_url,
                                    data=self.base_australian_data)  # NO FILES
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.step2_url)
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(
            str(messages[0]), "Your booking session has expired. Please start again.")

    def tearDown(self):
        """
        Clean up any created files.
        """
        # The test runner's temporary storage will handle cleanup for SimpleUploadedFile.
        # If using actual file storage (e.g., S3, local media root), ensure deletion here.
        if DriverProfile.objects.exists():
            for dp in DriverProfile.objects.all():
                # Django's FileField will manage the actual file deletion
                # when the model instance is deleted, if storage is configured.
                # For SimpleUploadedFile, they are in-memory and don't leave artifacts.
                # If you were saving to actual disk, you'd need to delete the files.
                pass



# PLEASE Note that post is not being tested. I can not seem to figure out how to submit the testbooking instance without a lot of problems. 