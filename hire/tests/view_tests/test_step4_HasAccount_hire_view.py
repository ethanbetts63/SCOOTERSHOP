import datetime
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.messages import get_messages
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from django.contrib.auth import get_user_model
from hire.models import TempHireBooking, DriverProfile, AddOn, Package
from dashboard.models import HireSettings
from hire.hire_pricing import calculate_booking_grand_total

# Import factories
from hire.model_factories import (
    create_user,
    create_motorcycle,
    create_hire_settings,
    create_temp_hire_booking,
    create_driver_profile,
    create_addon,
    create_package,
    create_temp_booking_addon,
)

User = get_user_model()


class Step4HasAccountViewTest(TestCase):
    """
    Tests for the HasAccountView (Step 4 of the hire booking process for logged-in users).
    """

    def setUp(self):
        """
        Set up common data for tests.
        """
        self.client = Client()
        self.user = create_user(username="testuser", email="test@example.com")
        self.client.login(username="testuser", password="password123")

        self.hire_settings = create_hire_settings(
            minimum_hire_duration_hours=2,
            maximum_hire_duration_days=30,
            hire_pricing_strategy='24_hour_customer_friendly',
            deposit_enabled=True,
            deposit_percentage=Decimal('10.00'),
            currency_code='AUD',
            currency_symbol='$',
        )
        self.motorcycle = create_motorcycle(
            daily_hire_rate=Decimal('100.00'),
            hourly_hire_rate=Decimal('20.00')
        )

        # Create a temporary booking for the session
        # Pickup: 1 day from now, 10:00
        # Return: 3 days from now, 16:00
        # This results in 2 full days + 6 hours excess (54 hours total)
        self.temp_booking = create_temp_hire_booking(
            motorcycle=self.motorcycle,
            pickup_date=timezone.now().date() + datetime.timedelta(days=1),
            pickup_time=datetime.time(10, 0),
            return_date=timezone.now().date() + datetime.timedelta(days=3),
            return_time=datetime.time(16, 0),
            has_motorcycle_license=True,
            is_international_booking=False,
        )
        self.client.session["temp_booking_id"] = self.temp_booking.id
        self.client.session["temp_booking_uuid"] = str(self.temp_booking.session_uuid)
        self.client.session.save()

        self.url = reverse("hire:step4_has_account")

        # Mock SimpleUploadedFile for image fields
        self.mock_image_file = SimpleUploadedFile(
            "test_image.jpg", b"file_content", content_type="image/jpeg"
        )

    def tearDown(self):
        """Clean up after tests."""
        # Ensure session is cleared
        if "temp_booking_id" in self.client.session:
            del self.client.session["temp_booking_id"]
        if "temp_booking_uuid" in self.client.session:
            del self.client.session["temp_booking_uuid"]
        self.client.session.save()

    # --- GET Request Tests ---

    def test_get_request_no_temp_booking(self):
        """
        Test GET request when temp_booking is not in session.
        Should redirect to step2_choose_bike with an error message.
        """
        del self.client.session["temp_booking_id"]
        del self.client.session["temp_booking_uuid"]
        self.client.session.save()

        response = self.client.get(self.url)
        self.assertRedirects(response, reverse("hire:step2_choose_bike"))
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Your booking session has expired. Please start again.")

    def test_get_request_existing_driver_profile(self):
        """
        Test GET request when an existing DriverProfile exists for the user.
        Form should be pre-populated.
        """
        existing_driver_profile = create_driver_profile(
            user=self.user,
            name="Existing Name",
            phone_number="0498765432",
            address_line_1="456 Old St",
            city="Melbourne",
            country="Australia",
            license_number="987654321",
            date_of_birth=timezone.now().date() - datetime.timedelta(days=365 * 25),
            license_expiry_date=timezone.now().date() + datetime.timedelta(days=365),
            is_australian_resident=True,
        )
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "hire/step4_has_account.html")

        form = response.context["form"]
        self.assertTrue(isinstance(form.instance, DriverProfile))
        self.assertEqual(form.instance.pk, existing_driver_profile.pk)
        self.assertEqual(form["name"].value(), "Existing Name")
        self.assertEqual(form["phone_number"].value(), "0498765432")

    def test_get_request_no_existing_driver_profile(self):
        """
        Test GET request when no existing DriverProfile exists for the user.
        A new unsaved instance should be passed to the form.
        """
        # Ensure no DriverProfile exists for this user
        DriverProfile.objects.filter(user=self.user).delete()

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "hire/step4_has_account.html")

        form = response.context["form"]
        self.assertTrue(isinstance(form.instance, DriverProfile))
        self.assertIsNone(form.instance.pk)  # Should be unsaved
        self.assertEqual(form.instance.user, self.user)
        # Check that default values are not pre-filled from a non-existent profile
        self.assertIsNone(form["name"].value()) # Should be None or empty for new instance

    def test_get_request_renders_template_and_context(self):
        """
        Test that the GET request renders the correct template with the correct context.
        """
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "hire/step4_has_account.html")
        self.assertIn("form", response.context)
        self.assertIn("temp_booking", response.context)
        self.assertEqual(response.context["temp_booking"], self.temp_booking)

    # --- POST Request Tests ---

    def test_post_request_no_temp_booking(self):
        """
        Test POST request when temp_booking is not in session.
        Should redirect to step2_choose_bike with an error message.
        """
        del self.client.session["temp_booking_id"]
        del self.client.session["temp_booking_uuid"]
        self.client.session.save()

        response = self.client.post(self.url, {})
        self.assertRedirects(response, reverse("hire:step2_choose_bike"))
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Your booking session has expired. Please start again.")

    def test_post_valid_submission_new_driver_profile(self):
        """
        Test a valid POST submission to create a new DriverProfile and update TempHireBooking.
        """
        # Ensure no DriverProfile exists for this user initially
        DriverProfile.objects.filter(user=self.user).delete()

        date_of_birth = timezone.now().date() - datetime.timedelta(days=365 * 25)
        license_expiry_date = timezone.now().date() + datetime.timedelta(days=365)

        post_data = {
            "name": "New Driver",
            "email": "new.driver@example.com",
            "phone_number": "0411111111",
            "address_line_1": "1 Test St",
            "city": "Sydney",
            "country": "Australia",
            "date_of_birth": date_of_birth.strftime("%Y-%m-%d"),
            "is_australian_resident": "on", # Checkbox value
            "license_number": "LIC12345",
            "license_expiry_date": license_expiry_date.strftime("%Y-%m-%d"),
            # No international license/passport fields for Australian resident
        }
        post_files = {
            "license_photo": self.mock_image_file,
        }

        response = self.client.post(self.url, data=post_data, files=post_files, follow=True)

        self.assertRedirects(response, reverse("hire:step5_summary_payment_options"))
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Driver details saved successfully.")

        # Verify DriverProfile was created
        driver_profile = DriverProfile.objects.get(user=self.user)
        self.assertEqual(driver_profile.name, "New Driver")
        self.assertEqual(driver_profile.license_number, "LIC12345")
        self.assertIsNotNone(driver_profile.license_photo)

        # Verify TempHireBooking was updated with the new driver profile and prices
        self.temp_booking.refresh_from_db()
        self.assertEqual(self.temp_booking.driver_profile, driver_profile)

        # Calculate expected prices based on the setup (2 full days + 6 hours excess)
        # Motorcycle: 100/day, 20/hour
        # Customer friendly: 2 * 100 + 6 * 20 = 200 + 120 = 320
        # Deposit: 10% of 320 = 32
        expected_motorcycle_price = Decimal('320.00')
        expected_grand_total = Decimal('320.00')
        expected_deposit_amount = Decimal('32.00')

        self.assertEqual(self.temp_booking.total_hire_price, expected_motorcycle_price)
        self.assertEqual(self.temp_booking.total_addons_price, Decimal('0.00'))
        self.assertEqual(self.temp_booking.total_package_price, Decimal('0.00'))
        self.assertEqual(self.temp_booking.grand_total, expected_grand_total)
        self.assertEqual(self.temp_booking.deposit_amount, expected_deposit_amount)
        self.assertEqual(self.temp_booking.currency, 'AUD')


    def test_post_valid_submission_existing_driver_profile(self):
        """
        Test a valid POST submission to update an existing DriverProfile and TempHireBooking.
        """
        existing_driver_profile = create_driver_profile(
            user=self.user,
            name="Original Name",
            phone_number="0499999999",
            address_line_1="10 Original St",
            city="Perth",
            country="Australia",
            license_number="ORIGINAL123",
            date_of_birth=timezone.now().date() - datetime.timedelta(days=365 * 30),
            license_expiry_date=timezone.now().date() + datetime.timedelta(days=365 * 2),
            is_australian_resident=True,
        )
        self.temp_booking.driver_profile = existing_driver_profile
        self.temp_booking.save()

        date_of_birth = timezone.now().date() - datetime.timedelta(days=365 * 25)
        license_expiry_date = timezone.now().date() + datetime.timedelta(days=365)

        post_data = {
            "name": "Updated Driver Name",
            "email": "updated.driver@example.com",
            "phone_number": "0422222222",
            "address_line_1": "2 Updated Ave",
            "city": "Brisbane",
            "country": "Australia",
            "date_of_birth": date_of_birth.strftime("%Y-%m-%d"),
            "is_australian_resident": "on",
            "license_number": "UPDATED678",
            "license_expiry_date": license_expiry_date.strftime("%Y-%m-%d"),
        }
        post_files = {
            "license_photo": self.mock_image_file,
        }

        response = self.client.post(self.url, data=post_data, files=post_files, follow=True)

        self.assertRedirects(response, reverse("hire:step5_summary_payment_options"))
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Driver details saved successfully.")

        # Verify DriverProfile was updated (not a new one created)
        updated_driver_profile = DriverProfile.objects.get(user=self.user)
        self.assertEqual(updated_driver_profile.pk, existing_driver_profile.pk)
        self.assertEqual(updated_driver_profile.name, "Updated Driver Name")
        self.assertEqual(updated_driver_profile.license_number, "UPDATED678")
        self.assertIsNotNone(updated_driver_profile.license_photo)

        # Verify TempHireBooking was updated with the existing driver profile and prices
        self.temp_booking.refresh_from_db()
        self.assertEqual(self.temp_booking.driver_profile, updated_driver_profile)

        # Prices should be recalculated based on the same temp_booking duration
        expected_motorcycle_price = Decimal('320.00')
        expected_grand_total = Decimal('320.00')
        expected_deposit_amount = Decimal('32.00')

        self.assertEqual(self.temp_booking.total_hire_price, expected_motorcycle_price)
        self.assertEqual(self.temp_booking.total_addons_price, Decimal('0.00'))
        self.assertEqual(self.temp_booking.total_package_price, Decimal('0.00'))
        self.assertEqual(self.temp_booking.grand_total, expected_grand_total)
        self.assertEqual(self.temp_booking.deposit_amount, expected_deposit_amount)
        self.assertEqual(self.temp_booking.currency, 'AUD')

    def test_post_invalid_submission(self):
        """
        Test an invalid POST submission (e.g., missing required fields).
        Should render the form again with errors and an error message.
        """
        # Missing 'name' and 'license_number' which are required
        post_data = {
            "email": "invalid@example.com",
            "phone_number": "0411111111",
            "address_line_1": "1 Test St",
            "city": "Sydney",
            "country": "Australia",
            "date_of_birth": (timezone.now().date() - datetime.timedelta(days=365 * 10)).strftime("%Y-%m-%d"), # Too young
            "is_australian_resident": "on",
            "license_expiry_date": (timezone.now().date() - datetime.timedelta(days=1)).strftime("%Y-%m-%d"), # Expired
        }
        # No files provided for required image fields

        response = self.client.post(self.url, data=post_data, follow=True)

        self.assertEqual(response.status_code, 200) # Should render the same page
        self.assertTemplateUsed(response, "hire/step4_has_account.html")
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Please correct the errors below.")

        form = response.context["form"]
        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)
        self.assertIn("license_number", form.errors)
        self.assertIn("date_of_birth", form.errors) # Should fail due to age
        self.assertIn("license_expiry_date", form.errors) # Should fail due to expiry
        self.assertIn("license_photo", form.errors) # Should fail due to missing file

        # Ensure no new DriverProfile was created if it was a new submission attempt
        self.assertEqual(DriverProfile.objects.filter(user=self.user).count(), 0)
        # Ensure temp_booking prices were not updated
        original_grand_total = self.temp_booking.grand_total
        self.temp_booking.refresh_from_db()
        self.assertEqual(self.temp_booking.grand_total, original_grand_total)


    def test_post_with_addons_and_package(self):
        """
        Test a valid POST submission with addons and a package selected in temp_booking.
        Ensure pricing is correctly calculated and updated.
        """
        addon1 = create_addon(name="GPS", daily_cost=Decimal('15.00'), hourly_cost=Decimal('3.00'))
        addon2 = create_addon(name="Gloves", daily_cost=Decimal('5.00'), hourly_cost=Decimal('1.00'))
        package = create_package(name="Touring Pack", daily_cost=Decimal('30.00'), hourly_cost=Decimal('5.00'))

        self.temp_booking.package = package
        self.temp_booking.save()
        create_temp_booking_addon(self.temp_booking, addon=addon1, quantity=1)
        create_temp_booking_addon(self.temp_booking, addon=addon2, quantity=2)
        self.temp_booking.refresh_from_db() # Reload to get related objects

        date_of_birth = timezone.now().date() - datetime.timedelta(days=365 * 25)
        license_expiry_date = timezone.now().date() + datetime.timedelta(days=365)

        post_data = {
            "name": "Addon Package Driver",
            "email": "addon.driver@example.com",
            "phone_number": "0433333333",
            "address_line_1": "3 Addon Rd",
            "city": "Adelaide",
            "country": "Australia",
            "date_of_birth": date_of_birth.strftime("%Y-%m-%d"),
            "is_australian_resident": "on",
            "license_number": "ADDONLIC",
            "license_expiry_date": license_expiry_date.strftime("%Y-%m-%d"),
        }
        post_files = {
            "license_photo": self.mock_image_file,
        }

        response = self.client.post(self.url, data=post_data, files=post_files, follow=True)

        self.assertRedirects(response, reverse("hire:step5_summary_payment_options"))
        self.temp_booking.refresh_from_db()

        # Recalculate expected prices based on the temp_booking and selected items
        # Duration: 2 full days + 6 hours excess (54 hours total)
        # Motorcycle: 2 * 100 (daily) + 6 * 20 (hourly) = 200 + 120 = 320
        # Package: Touring Pack (daily_cost=30, hourly_cost=5) -> 2 * 30 + 6 * 5 = 60 + 30 = 90
        # Addon1 (GPS): 1 quantity (daily_cost=15, hourly_cost=3) -> 2 * 15 + 6 * 3 = 30 + 18 = 48
        # Addon2 (Gloves): 2 quantity (daily_cost=5, hourly_cost=1) -> 2 * (2 * 5) + 6 * (2 * 1) = 20 + 12 = 32
        # Total Addons: 48 + 32 = 80

        expected_motorcycle_price = Decimal('320.00')
        expected_package_price = Decimal('90.00')
        expected_addons_price = Decimal('80.00')
        expected_grand_total = expected_motorcycle_price + expected_package_price + expected_addons_price
        expected_deposit_amount = expected_grand_total * Decimal('0.10') # 10% deposit

        self.assertEqual(self.temp_booking.total_hire_price, expected_motorcycle_price)
        self.assertEqual(self.temp_booking.total_package_price, expected_package_price)
        self.assertEqual(self.temp_booking.total_addons_price, expected_addons_price)
        self.assertEqual(self.temp_booking.grand_total, expected_grand_total)
        self.assertEqual(self.temp_booking.deposit_amount, expected_deposit_amount)
        self.assertEqual(self.temp_booking.currency, 'AUD')

        # Verify DriverProfile was created
        driver_profile = DriverProfile.objects.get(user=self.user)
        self.assertEqual(driver_profile.name, "Addon Package Driver")
        self.assertEqual(self.temp_booking.driver_profile, driver_profile)

    def test_post_valid_submission_international_resident(self):
        """
        Test a valid POST submission for an international resident.
        """
        # Ensure no DriverProfile exists for this user initially
        DriverProfile.objects.filter(user=self.user).delete()

        date_of_birth = timezone.now().date() - datetime.timedelta(days=365 * 25)
        international_license_expiry_date = timezone.now().date() + datetime.timedelta(days=365)
        passport_expiry_date = timezone.now().date() + datetime.timedelta(days=365)

        post_data = {
            "name": "International Driver",
            "email": "international.driver@example.com",
            "phone_number": "0444444444",
            "address_line_1": "10 International St",
            "city": "London",
            "country": "United Kingdom",
            "date_of_birth": date_of_birth.strftime("%Y-%m-%d"),
            "is_australian_resident": "", # Checkbox not checked, means False
            "license_number": "INTL12345", # This is the primary license field, still required
            "license_expiry_date": (timezone.now().date() + datetime.timedelta(days=365)).strftime("%Y-%m-%d"), # Primary license expiry
            "international_license_issuing_country": "UK",
            "international_license_expiry_date": international_license_expiry_date.strftime("%Y-%m-%d"),
            "passport_number": "PASS12345",
            "passport_expiry_date": passport_expiry_date.strftime("%Y-%m-%d"),
        }
        post_files = {
            "license_photo": self.mock_image_file,
            "international_license_photo": self.mock_image_file,
            "passport_photo": self.mock_image_file,
            "id_image": self.mock_image_file, # Assuming this is required for international
            "international_id_image": self.mock_image_file,
        }

        response = self.client.post(self.url, data=post_data, files=post_files, follow=True)

        self.assertRedirects(response, reverse("hire:step5_summary_payment_options"))
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(str(messages[0]), "Driver details saved successfully.")

        driver_profile = DriverProfile.objects.get(user=self.user)
        self.assertEqual(driver_profile.name, "International Driver")
        self.assertFalse(driver_profile.is_australian_resident)
        self.assertEqual(driver_profile.international_license_issuing_country, "UK")
        self.assertEqual(driver_profile.passport_number, "PASS12345")
        self.assertIsNotNone(driver_profile.international_license_photo)
        self.assertIsNotNone(driver_profile.passport_photo)
        self.assertIsNotNone(driver_profile.id_image)
        self.assertIsNotNone(driver_profile.international_id_image)

        self.temp_booking.refresh_from_db()
        self.assertEqual(self.temp_booking.driver_profile, driver_profile)
        # Prices should still be calculated the same way
        expected_motorcycle_price = Decimal('320.00')
        expected_grand_total = Decimal('320.00')
        expected_deposit_amount = Decimal('32.00')
        self.assertEqual(self.temp_booking.grand_total, expected_grand_total)
        self.assertEqual(self.temp_booking.deposit_amount, expected_deposit_amount)
