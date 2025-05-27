import datetime
from decimal import Decimal
from unittest.mock import patch
import uuid # Import uuid module for UUID object conversion
import json # For printing form errors

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.messages import get_messages
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from django.contrib.sessions.models import Session # For debugging session persistence

from django.contrib.auth import get_user_model
from hire.models import TempHireBooking, DriverProfile, AddOn, Package
from dashboard.models import HireSettings
from hire.hire_pricing import calculate_booking_grand_total

# Import factories from the specified path
from hire.tests.test_helpers.model_factories import (
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

    def _set_session_data(self, temp_booking_instance):
        """Helper to consistently set session data."""
        session = self.client.session
        session["temp_booking_uuid"] = str(temp_booking_instance.session_uuid)
        session.save()
        print(f"DEBUG_TEST: Session data set in _set_session_data: temp_booking_uuid={str(temp_booking_instance.session_uuid)}")
        retrieved_uuid = self.client.session.get("temp_booking_uuid")
        print(f"DEBUG_TEST: Verified temp_booking_uuid in client.session: {retrieved_uuid}")
        self.assertIsNotNone(retrieved_uuid, "temp_booking_uuid should be in client.session after setting.")


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
            minimum_driver_age=18, # Ensure this is set for age validation
        )
        self.motorcycle = create_motorcycle(
            daily_hire_rate=Decimal('100.00'),
            hourly_hire_rate=Decimal('20.00')
        )

        # This self.temp_booking can be used for GET tests or as a base for POST tests
        # For POST tests, it's often better to create a fresh one to avoid state issues.
        self.temp_booking = create_temp_hire_booking(
            motorcycle=self.motorcycle,
            pickup_date=timezone.now().date() + datetime.timedelta(days=1),
            pickup_time=datetime.time(10, 0),
            return_date=timezone.now().date() + datetime.timedelta(days=3), # Results in 2 full days + 6 hours
            return_time=datetime.time(16, 0),
            has_motorcycle_license=True,
            is_international_booking=False, # Default to Australian context for some tests
            session_uuid=uuid.uuid4() 
        )
        
        self._set_session_data(self.temp_booking) # Set session for the initial self.temp_booking

        self.url = reverse("hire:step4_has_account")

        # Create distinct mock files for each potential upload
        self.mock_license_photo = SimpleUploadedFile("license.jpg", b"license_content", "image/jpeg")
        self.mock_intl_license_photo = SimpleUploadedFile("intl_license.jpg", b"intl_license_content", "image/jpeg")
        self.mock_passport_photo = SimpleUploadedFile("passport.jpg", b"passport_content", "image/jpeg")
        # id_image and international_id_image are in form fields but not dynamically required by form __init__
        # For now, we'll only include them if a test specifically needs to provide them.
        # If model makes them non-nullable, tests might fail if they are not provided.
        self.mock_id_image = SimpleUploadedFile("id_image.jpg", b"id_image_content", "image/jpeg")
        self.mock_intl_id_image = SimpleUploadedFile("intl_id_image.jpg", b"intl_id_image_content", "image/jpeg")


    def tearDown(self):
        pass


    # --- GET Request Tests ---

    def test_get_request_no_temp_booking_in_session(self):
        session = self.client.session
        session.pop("temp_booking_uuid", None)
        session.save()
        print("DEBUG_TEST: Popped 'temp_booking_uuid' for test_get_request_no_temp_booking_in_session")

        response = self.client.get(self.url)
        self.assertRedirects(response, reverse("hire:step2_choose_bike"))
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Your booking session has expired. Please start again.")

    def test_get_request_existing_driver_profile(self):
        existing_driver_profile = create_driver_profile(
            user=self.user,
            name="Existing Name",
            phone_number="0498765432",
            is_australian_resident=True # Explicitly set for clarity
        )
        self.temp_booking.driver_profile = existing_driver_profile
        self.temp_booking.save() 

        self._set_session_data(self.temp_booking)

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200, f"Response content: {response.content.decode() if response.status_code != 200 else 'OK'}")
        self.assertTemplateUsed(response, "hire/step4_has_account.html")

        form = response.context["form"]
        self.assertTrue(isinstance(form.instance, DriverProfile))
        self.assertEqual(form.instance.pk, existing_driver_profile.pk)
        self.assertEqual(form["name"].value(), "Existing Name")
        # Check the ChoiceField initial value
        self.assertEqual(form['is_australian_resident'].value(), 'True')


    def test_get_request_no_existing_driver_profile(self):
        DriverProfile.objects.filter(user=self.user).delete()
        # Ensure self.temp_booking is clean for this test or use a fresh one
        current_temp_booking = create_temp_hire_booking(
             motorcycle=self.motorcycle, session_uuid=uuid.uuid4(),
             pickup_date=self.temp_booking.pickup_date, pickup_time=self.temp_booking.pickup_time,
             return_date=self.temp_booking.return_date, return_time=self.temp_booking.return_time
        )
        self._set_session_data(current_temp_booking) 

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200, f"Response content: {response.content.decode() if response.status_code != 200 else 'OK'}")
        self.assertTemplateUsed(response, "hire/step4_has_account.html")

        form = response.context["form"]
        self.assertTrue(isinstance(form.instance, DriverProfile))
        self.assertIsNone(form.instance.pk)
        self.assertEqual(form.instance.user, self.user)
        self.assertEqual(form["name"].value(), '') # Corrected: CharField initial is ''
        # Default for is_australian_resident in form __init__ is True if no other info
        self.assertEqual(form['is_australian_resident'].value(), 'True')


    def test_get_request_renders_template_and_context(self):
        self._set_session_data(self.temp_booking)

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200, f"Response content: {response.content.decode() if response.status_code != 200 else 'OK'}")
        self.assertTemplateUsed(response, "hire/step4_has_account.html")
        self.assertIn("form", response.context)
        self.assertIn("temp_booking", response.context)
        self.assertEqual(response.context["temp_booking"], self.temp_booking)

    # --- POST Request Tests ---

    def test_post_request_no_temp_booking_in_session(self):
        session = self.client.session
        session.pop("temp_booking_uuid", None)
        session.save()
        print("DEBUG_TEST: Popped 'temp_booking_uuid' for test_post_request_no_temp_booking_in_session")

        response = self.client.post(self.url, {})
        self.assertRedirects(response, reverse("hire:step2_choose_bike"))
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Your booking session has expired. Please start again.")

    def test_post_valid_submission_new_driver_profile_australian(self):
        DriverProfile.objects.filter(user=self.user).delete()
        
        current_temp_booking = create_temp_hire_booking(
            motorcycle=self.motorcycle, session_uuid=uuid.uuid4(),
            pickup_date=self.temp_booking.pickup_date, pickup_time=self.temp_booking.pickup_time,
            return_date=self.temp_booking.return_date, return_time=self.temp_booking.return_time
        )
        self._set_session_data(current_temp_booking) 

        min_age = self.hire_settings.minimum_driver_age
        date_of_birth = timezone.now().date() - datetime.timedelta(days=365 * (min_age + 2)) # Ensure old enough
        license_expiry_date = current_temp_booking.return_date + datetime.timedelta(days=30) # Ensure valid post-booking

        post_data = {
            "name": "New Aussie Driver", "email": "new.aussie@example.com", "phone_number": "0411111111",
            "address_line_1": "1 Test St", "city": "Sydney", "state": "NSW", "post_code": "2000", "country": "Australia",
            "date_of_birth": date_of_birth.strftime("%Y-%m-%d"), 
            "is_australian_resident": "True", # Explicitly "True"
            "license_number": "AUSLIC12345", "license_expiry_date": license_expiry_date.strftime("%Y-%m-%d"),
        }
        self.mock_license_photo.seek(0)
        post_files = {"license_photo": self.mock_license_photo}

        response = self.client.post(self.url, data=post_data, files=post_files, follow=False) 
        
        if response.status_code != 302:
            form_errors = response.context['form'].errors.as_json() if 'form' in response.context and hasattr(response.context['form'], 'errors') else "No form or errors in context"
            print(f"DEBUG_TEST: Form errors (new_aussie_driver): {form_errors}")
        
        self.assertEqual(response.status_code, 302, f"Expected redirect, got {response.status_code}. Errors: {form_errors if 'form_errors' in locals() else 'N/A'}")
        self.assertRedirects(response, reverse("hire:step5_summary_payment_options"))
        
        # To check messages, you might need to make a GET request to the redirected page or handle session messages differently
        # For simplicity, we'll assume the redirect implies success if status is 302.

        driver_profile = DriverProfile.objects.get(user=self.user)
        self.assertEqual(driver_profile.name, "New Aussie Driver")
        self.assertTrue(driver_profile.is_australian_resident)
        current_temp_booking.refresh_from_db()
        self.assertEqual(current_temp_booking.driver_profile, driver_profile)

        expected_motorcycle_price = Decimal('320.00') 
        expected_grand_total = Decimal('320.00')
        expected_deposit_amount = Decimal('32.00')
        self.assertEqual(current_temp_booking.total_hire_price, expected_motorcycle_price)
        self.assertEqual(current_temp_booking.grand_total, expected_grand_total)
        self.assertEqual(current_temp_booking.deposit_amount, expected_deposit_amount)


    def test_post_valid_submission_existing_driver_profile_australian(self):
        min_age = self.hire_settings.minimum_driver_age
        dob = timezone.now().date() - datetime.timedelta(days=365 * (min_age + 5))
        lic_exp = timezone.now().date() + datetime.timedelta(days=365 * 2)

        existing_driver_profile = create_driver_profile(
            user=self.user, name="Original Aussie", license_number="OLDLIC123",
            is_australian_resident=True, date_of_birth=dob, license_expiry_date=lic_exp,
            license_photo=SimpleUploadedFile("orig_lic.jpg", b"content", "image/jpeg") # Existing photo
        )
        
        current_temp_booking = create_temp_hire_booking(
            motorcycle=self.motorcycle, driver_profile=existing_driver_profile, session_uuid=uuid.uuid4(),
            pickup_date=self.temp_booking.pickup_date, pickup_time=self.temp_booking.pickup_time,
            return_date=self.temp_booking.return_date, return_time=self.temp_booking.return_time
        )
        self._set_session_data(current_temp_booking)

        updated_dob = timezone.now().date() - datetime.timedelta(days=365 * (min_age + 3))
        updated_lic_exp = current_temp_booking.return_date + datetime.timedelta(days=60)

        post_data = {
            "name": "Updated Aussie Driver", "email": "updated.aussie@example.com", "phone_number": "0422222222",
            "address_line_1": "2 Updated Ave", "city": "Brisbane", "state": "QLD", "post_code": "4000", "country": "Australia",
            "date_of_birth": updated_dob.strftime("%Y-%m-%d"), 
            "is_australian_resident": "True",
            "license_number": "NEWLIC678", "license_expiry_date": updated_lic_exp.strftime("%Y-%m-%d"),
        }
        # Optionally update the photo, or test keeping the old one if no new file is provided.
        # If a new photo is provided, it should replace the old one.
        # If no new photo is provided, and the field is required, it should use existing.
        # The form logic `if not license_photo and not (self.instance and self.instance.license_photo):` handles this.
        # Let's test *not* providing a new photo to see if existing is kept.
        post_files = {} 
        # If testing photo update:
        # self.mock_license_photo.seek(0)
        # post_files = {"license_photo": self.mock_license_photo}


        response = self.client.post(self.url, data=post_data, files=post_files, follow=False)
        
        form_errors = "No form errors"
        if response.status_code != 302:
            if 'form' in response.context and hasattr(response.context['form'], 'errors'):
                form_errors = response.context['form'].errors.as_json()
            print(f"DEBUG_TEST: Form errors (existing_aussie_driver): {form_errors}")
        
        self.assertEqual(response.status_code, 302, f"Expected redirect. Errors: {form_errors}")
        self.assertRedirects(response, reverse("hire:step5_summary_payment_options"))

        updated_driver_profile = DriverProfile.objects.get(user=self.user)
        self.assertEqual(updated_driver_profile.pk, existing_driver_profile.pk)
        self.assertEqual(updated_driver_profile.name, "Updated Aussie Driver")
        self.assertTrue(updated_driver_profile.license_photo is not None) # Check existing photo was kept

        current_temp_booking.refresh_from_db()
        self.assertEqual(current_temp_booking.driver_profile, updated_driver_profile)
        self.assertEqual(current_temp_booking.grand_total, Decimal('320.00'))


    def test_post_invalid_submission_australian(self):
        self._set_session_data(self.temp_booking) # Uses the default self.temp_booking
        # Missing many required fields for an Australian resident (default)
        post_data = {
            "name": "", # Invalid
            "is_australian_resident": "True", # Explicitly set for clarity of what's being tested
            # Other fields like license_number, license_expiry_date, dob, phone, address, city, country, license_photo are missing
        } 
        
        response = self.client.post(self.url, data=post_data) 
        self.assertEqual(response.status_code, 200) 
        self.assertTemplateUsed(response, "hire/step4_has_account.html")
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any(str(msg) == "Please correct the errors below." for msg in messages))
        
        form = response.context["form"]
        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)
        self.assertIn("phone_number", form.errors)
        self.assertIn("address_line_1", form.errors)
        self.assertIn("city", form.errors)
        self.assertIn("country", form.errors)
        self.assertIn("date_of_birth", form.errors)
        self.assertIn("license_number", form.errors)
        self.assertIn("license_expiry_date", form.errors)
        self.assertIn("license_photo", form.errors) # Required for Aussie


    def test_post_with_addons_and_package_australian(self):
        addon1 = create_addon(name="GPS", daily_cost=Decimal('15.00'), hourly_cost=Decimal('3.00'))
        package1 = create_package(name="Touring Pack", daily_cost=Decimal('30.00'), hourly_cost=Decimal('5.00'))
        
        current_temp_booking = create_temp_hire_booking(
            motorcycle=self.motorcycle, package=package1, session_uuid=uuid.uuid4(),
            pickup_date=self.temp_booking.pickup_date, pickup_time=self.temp_booking.pickup_time,
            return_date=self.temp_booking.return_date, return_time=self.temp_booking.return_time
        )
        create_temp_booking_addon(current_temp_booking, addon=addon1, quantity=1)
        self._set_session_data(current_temp_booking)

        min_age = self.hire_settings.minimum_driver_age
        date_of_birth = timezone.now().date() - datetime.timedelta(days=365 * (min_age + 2))
        license_expiry_date = current_temp_booking.return_date + datetime.timedelta(days=30)

        post_data = {
            "name": "Addon Aussie Driver", "email": "addon.aussie@example.com", "phone_number": "0433333333",
            "address_line_1": "3 Addon Rd", "city": "Adelaide", "state": "SA", "post_code": "5000", "country": "Australia",
            "date_of_birth": date_of_birth.strftime("%Y-%m-%d"), 
            "is_australian_resident": "True",
            "license_number": "ADDONLICSA", "license_expiry_date": license_expiry_date.strftime("%Y-%m-%d"),
        }
        self.mock_license_photo.seek(0)
        post_files = {"license_photo": self.mock_license_photo}

        response = self.client.post(self.url, data=post_data, files=post_files, follow=False)
        
        form_errors = "No form errors"
        if response.status_code != 302:
            if 'form' in response.context and hasattr(response.context['form'], 'errors'):
                form_errors = response.context['form'].errors.as_json()
            print(f"DEBUG_TEST: Form errors (addons_aussie): {form_errors}")

        self.assertEqual(response.status_code, 302, f"Expected redirect. Errors: {form_errors}")
        self.assertRedirects(response, reverse("hire:step5_summary_payment_options"))

        current_temp_booking.refresh_from_db()
        expected_motorcycle_price = Decimal('320.00')
        expected_package_price = Decimal('90.00') # 2 days * 30 + 6 hrs * 5
        expected_addons_price = Decimal('48.00')  # 1 * (2 days * 15 + 6 hrs * 3)
        expected_grand_total = expected_motorcycle_price + expected_package_price + expected_addons_price 
        
        self.assertEqual(current_temp_booking.total_hire_price, expected_motorcycle_price)
        self.assertEqual(current_temp_booking.total_package_price, expected_package_price)
        self.assertEqual(current_temp_booking.total_addons_price, expected_addons_price)
        self.assertEqual(current_temp_booking.grand_total, expected_grand_total)


    def test_post_valid_submission_international_resident(self):
        DriverProfile.objects.filter(user=self.user).delete()
        
        current_temp_booking = create_temp_hire_booking(
            motorcycle=self.motorcycle, session_uuid=uuid.uuid4(),
            pickup_date=self.temp_booking.pickup_date, pickup_time=self.temp_booking.pickup_time,
            return_date=self.temp_booking.return_date, return_time=self.temp_booking.return_time
        )
        self._set_session_data(current_temp_booking)

        min_age = self.hire_settings.minimum_driver_age
        date_of_birth = timezone.now().date() - datetime.timedelta(days=365 * (min_age + 4))
        # For international, domestic license fields are not primary, but intl and passport are
        intl_license_expiry_date = current_temp_booking.return_date + datetime.timedelta(days=45)
        passport_expiry_date = current_temp_booking.return_date + datetime.timedelta(days=90)
        # Domestic license fields should NOT be required by the form for international
        # but the model might still require them if not blank=True.
        # The form explicitly makes them not required, so we don't need to provide them.

        post_data = {
            "name": "International Driver", "email": "int.driver@example.com", "phone_number": "+447123456789",
            "address_line_1": "10 Downing St", "city": "London", "country": "United Kingdom", # No state/postcode for UK typically
            "date_of_birth": date_of_birth.strftime("%Y-%m-%d"), 
            "is_australian_resident": "False", # Explicitly "False"
            # Australian license details should be omitted as per form logic for non-Australians
            # "license_number": "", 
            # "license_expiry_date": "",
            "international_license_issuing_country": "UK",
            "international_license_expiry_date": intl_license_expiry_date.strftime("%Y-%m-%d"),
            "passport_number": "PASSUK12345",
            "passport_expiry_date": passport_expiry_date.strftime("%Y-%m-%d"),
        }
        self.mock_intl_license_photo.seek(0)
        self.mock_passport_photo.seek(0)
        # id_image and international_id_image are not made required by form logic based on residency
        # but if your model requires them, you'd need to add them.
        # For now, only providing what the form explicitly makes required.
        post_files = { 
            "international_license_photo": self.mock_intl_license_photo,
            "passport_photo": self.mock_passport_photo,
            # "id_image": self.mock_id_image, # If required by model / other validation
            # "international_id_image": self.mock_intl_id_image # If required
        }

        response = self.client.post(self.url, data=post_data, files=post_files, follow=False)
        
        form_errors = "No form errors"
        if response.status_code != 302:
            if 'form' in response.context and hasattr(response.context['form'], 'errors'):
                form_errors = response.context['form'].errors.as_json()
            print(f"DEBUG_TEST: Form errors (international_resident): {form_errors}")
        
        self.assertEqual(response.status_code, 302, f"Expected redirect. Errors: {form_errors}")
        self.assertRedirects(response, reverse("hire:step5_summary_payment_options"))

        driver_profile = DriverProfile.objects.get(user=self.user)
        self.assertEqual(driver_profile.name, "International Driver")
        self.assertFalse(driver_profile.is_australian_resident)
        current_temp_booking.refresh_from_db()
        self.assertEqual(current_temp_booking.grand_total, Decimal('320.00'))
        self.assertEqual(driver_profile.international_license_issuing_country, "UK")
        self.assertEqual(driver_profile.passport_number, "PASSUK12345")
