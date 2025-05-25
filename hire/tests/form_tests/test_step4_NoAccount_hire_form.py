# hire/tests/form_tests/test_step4_NoAccount_hire_form.py

from django.test import TestCase
from django.core.exceptions import ValidationError
import datetime
from django.utils import timezone
from unittest.mock import MagicMock
from django.core.files.uploadedfile import SimpleUploadedFile # Import SimpleUploadedFile

from hire.forms.step4_NoAccount_form import Step4NoAccountForm
from hire.tests.test_helpers.model_factories import create_driver_profile, create_temp_hire_booking

class Step4NoAccountFormTests(TestCase):
    """
    Tests for the Step4NoAccountForm, focusing on its clean method.
    """

    def setUp(self):
        """
        Set up common data for tests.
        """
        self.return_date_future = timezone.now().date() + datetime.timedelta(days=30)
        self.return_date_past = timezone.now().date() - datetime.timedelta(days=30)

        # Mock TempHireBooking for validation
        self.temp_booking_future_return = MagicMock()
        self.temp_booking_future_return.return_date = self.return_date_future

        self.temp_booking_past_return = MagicMock()
        self.temp_booking_past_return.return_date = self.return_date_past

        # Create dummy files for testing photo uploads
        self.dummy_license = SimpleUploadedFile("license.jpg", b"file_content", content_type="image/jpeg")
        self.dummy_int_license = SimpleUploadedFile("int_license.jpg", b"file_content", content_type="image/jpeg")
        self.dummy_passport = SimpleUploadedFile("passport.jpg", b"file_content", content_type="image/jpeg")


        # Base form data for an Australian resident (valid state)
        self.base_australian_data = {
            'name': 'Jane Doe',
            'email': 'jane.doe@example.com',
            'phone_number': '0412345678',
            'address_line_1': '100 Main St',
            'city': 'Melbourne',
            'country': 'Australia',
            'date_of_birth': datetime.date(1990, 1, 1),
            'is_australian_resident': 'True', # Note: ChoiceField returns string
            'license_number': 'AUS12345',
            'license_expiry_date': self.return_date_future + datetime.timedelta(days=1),
            'license_photo': self.dummy_license, # Use SimpleUploadedFile
            # Ensure international/passport fields are empty/None for Australian residents
            'international_license_photo': None,
            'international_license_issuing_country': '',
            'international_license_expiry_date': None,
            'passport_photo': None,
            'passport_number': '',
            'passport_expiry_date': None,
        }

        # Base form data for a foreign resident (valid state)
        self.base_foreign_data = {
            'name': 'John Foreigner',
            'email': 'john.f@example.com',
            'phone_number': '0123456789',
            'address_line_1': '10 International Blvd',
            'city': 'Sydney',
            'country': 'USA',
            'date_of_birth': datetime.date(1985, 5, 10),
            'is_australian_resident': 'False', # Note: ChoiceField returns string
            'international_license_photo': self.dummy_int_license, # Use SimpleUploadedFile
            'international_license_issuing_country': 'USA',
            'international_license_expiry_date': self.return_date_future + datetime.timedelta(days=1),
            'passport_photo': self.dummy_passport, # Use SimpleUploadedFile
            'passport_number': 'P1234567',
            'passport_expiry_date': self.return_date_future + datetime.timedelta(days=1),
            # Ensure Australian-specific fields are empty/None for foreign residents
            'license_number': '',
            'license_expiry_date': None,
        }


    # --- Australian Resident Tests ---
    def test_clean_valid_australian_resident(self):
        """
        Test a valid submission for an Australian resident.
        """
        form_data = self.base_australian_data.copy()
        # For file uploads, files need to be passed separately to the form
        form = Step4NoAccountForm(data=form_data, files={
            'license_photo': self.dummy_license
        }, temp_booking=self.temp_booking_future_return)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['is_australian_resident'], 'True')

    def test_clean_australian_resident_missing_license_photo(self):
        """
        Test missing license photo for an Australian resident.
        """
        form_data = self.base_australian_data.copy()
        # Do not pass 'license_photo' in files to simulate missing upload
        form = Step4NoAccountForm(data=form_data, temp_booking=self.temp_booking_future_return)
        self.assertFalse(form.is_valid())
        self.assertIn('license_photo', form.errors)
        self.assertIn("Australian residents must upload their domestic driver's license photo.", form.errors['license_photo'])


    def test_clean_australian_resident_missing_license_number(self):
        """
        Test missing license number for an Australian resident.
        """
        form_data = self.base_australian_data.copy()
        form_data['license_number'] = '' # Explicitly missing
        # Ensure files are passed for other validations to pass
        form = Step4NoAccountForm(data=form_data, files={
            'license_photo': self.dummy_license
        }, temp_booking=self.temp_booking_future_return)
        self.assertFalse(form.is_valid())
        self.assertIn('license_number', form.errors)
        self.assertIn("Australian residents must provide their domestic license number.", form.errors['license_number'])

    def test_clean_australian_resident_license_expired_before_return(self):
        """
        Test Australian license expiry date before return date.
        """
        form_data = self.base_australian_data.copy()
        form_data['license_expiry_date'] = self.return_date_future - datetime.timedelta(days=1) # Before return date
        # Ensure files are passed for other validations to pass
        form = Step4NoAccountForm(data=form_data, files={
            'license_photo': self.dummy_license
        }, temp_booking=self.temp_booking_future_return)
        self.assertFalse(form.is_valid())
        self.assertIn('license_expiry_date', form.errors)
        self.assertIn("Your Australian Driver's License must not expire before the end of your booking.", form.errors['license_expiry_date'])
    
    def test_clean_australian_resident_missing_license_expiry_date(self):
        """
        Test missing license expiry date for an Australian resident.
        """
        form_data = self.base_australian_data.copy()
        form_data['license_expiry_date'] = None # Explicitly missing
        # Ensure files are passed for other validations to pass
        form = Step4NoAccountForm(data=form_data, files={
            'license_photo': self.dummy_license
        }, temp_booking=self.temp_booking_future_return)
        self.assertFalse(form.is_valid())
        self.assertIn('license_expiry_date', form.errors)
        self.assertIn("Australian residents must provide their domestic license expiry date.", form.errors['license_expiry_date'])


    # --- Foreign Resident Tests ---
    def test_clean_valid_foreign_resident(self):
        """
        Test a valid submission for a foreign resident.
        """
        form_data = self.base_foreign_data.copy()
        # For file uploads, files need to be passed separately to the form
        form = Step4NoAccountForm(data=form_data, files={
            'international_license_photo': self.dummy_int_license,
            'passport_photo': self.dummy_passport
        }, temp_booking=self.temp_booking_future_return)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['is_australian_resident'], 'False')

    def test_clean_foreign_resident_missing_international_license_photo(self):
        """
        Test missing international license photo for a foreign resident.
        """
        form_data = self.base_foreign_data.copy()
        # Do not pass 'international_license_photo' in files to simulate missing upload
        form = Step4NoAccountForm(data=form_data, files={
            'passport_photo': self.dummy_passport # Still pass passport photo
        }, temp_booking=self.temp_booking_future_return)
        self.assertFalse(form.is_valid())
        self.assertIn('international_license_photo', form.errors)
        self.assertIn("Foreign drivers must upload their International Driver's License photo.", form.errors['international_license_photo'])

    def test_clean_foreign_resident_missing_passport_photo(self):
        """
        Test missing passport photo for a foreign resident.
        """
        form_data = self.base_foreign_data.copy()
        # Do not pass 'passport_photo' in files to simulate missing upload
        form = Step4NoAccountForm(data=form_data, files={
            'international_license_photo': self.dummy_int_license # Still pass international license photo
        }, temp_booking=self.temp_booking_future_return)
        self.assertFalse(form.is_valid())
        self.assertIn('passport_photo', form.errors)
        self.assertIn("Foreign drivers must upload their passport photo.", form.errors['passport_photo'])

    def test_clean_foreign_resident_missing_international_license_country(self):
        """
        Test missing international license issuing country for a foreign resident.
        """
        form_data = self.base_foreign_data.copy()
        form_data['international_license_issuing_country'] = '' # Explicitly missing
        # Ensure files are passed for other validations to pass
        form = Step4NoAccountForm(data=form_data, files={
            'international_license_photo': self.dummy_int_license,
            'passport_photo': self.dummy_passport
        }, temp_booking=self.temp_booking_future_return)
        self.assertFalse(form.is_valid())
        self.assertIn('international_license_issuing_country', form.errors)
        self.assertIn("Foreign drivers must provide the issuing country of their International Driver's License.", form.errors['international_license_issuing_country'])

    def test_clean_foreign_resident_missing_international_license_expiry_date(self):
        """
        Test missing international license expiry date for a foreign resident.
        """
        form_data = self.base_foreign_data.copy()
        form_data['international_license_expiry_date'] = None # Explicitly missing
        # Ensure files are passed for other validations to pass
        form = Step4NoAccountForm(data=form_data, files={
            'international_license_photo': self.dummy_int_license,
            'passport_photo': self.dummy_passport
        }, temp_booking=self.temp_booking_future_return)
        self.assertFalse(form.is_valid())
        self.assertIn('international_license_expiry_date', form.errors)
        self.assertIn("Foreign drivers must provide the expiry date of their International Driver's License.", form.errors['international_license_expiry_date'])

    def test_clean_foreign_resident_international_license_expired_before_return(self):
        """
        Test international license expiry date before return date.
        """
        form_data = self.base_foreign_data.copy()
        form_data['international_license_expiry_date'] = self.return_date_future - datetime.timedelta(days=1) # Before return date
        # Ensure files are passed for other validations to pass
        form = Step4NoAccountForm(data=form_data, files={
            'international_license_photo': self.dummy_int_license,
            'passport_photo': self.dummy_passport
        }, temp_booking=self.temp_booking_future_return)
        self.assertFalse(form.is_valid())
        self.assertIn('international_license_expiry_date', form.errors)
        self.assertIn("Your International Driver's License must not expire before the end of your booking.", form.errors['international_license_expiry_date'])

    def test_clean_foreign_resident_missing_passport_number(self):
        """
        Test missing passport number for a foreign resident.
        """
        form_data = self.base_foreign_data.copy()
        form_data['passport_number'] = '' # Explicitly missing
        # Ensure files are passed for other validations to pass
        form = Step4NoAccountForm(data=form_data, files={
            'international_license_photo': self.dummy_int_license,
            'passport_photo': self.dummy_passport
        }, temp_booking=self.temp_booking_future_return)
        self.assertFalse(form.is_valid())
        self.assertIn('passport_number', form.errors)
        self.assertIn("Foreign drivers must provide their passport number.", form.errors['passport_number'])

    def test_clean_foreign_resident_missing_passport_expiry_date(self):
        """
        Test missing passport expiry date for a foreign resident.
        """
        form_data = self.base_foreign_data.copy()
        form_data['passport_expiry_date'] = None # Explicitly missing
        # Ensure files are passed for other validations to pass
        form = Step4NoAccountForm(data=form_data, files={
            'international_license_photo': self.dummy_int_license,
            'passport_photo': self.dummy_passport
        }, temp_booking=self.temp_booking_future_return)
        self.assertFalse(form.is_valid())
        self.assertIn('passport_expiry_date', form.errors)
        self.assertIn("Foreign drivers must provide their passport expiry date.", form.errors['passport_expiry_date'])

    def test_clean_foreign_resident_passport_expired_before_return(self):
        """
        Test passport expiry date before return date.
        """
        form_data = self.base_foreign_data.copy()
        form_data['passport_expiry_date'] = self.return_date_future - datetime.timedelta(days=1) # Before return date
        # Ensure other fields are valid so this specific error can be tested in isolation
        form_data['international_license_issuing_country'] = 'USA' # Ensure this is present
        form_data['international_license_expiry_date'] = self.return_date_future + datetime.timedelta(days=1) # Ensure this is valid
        form_data['passport_number'] = 'P1234567' # Ensure this is present

        # Ensure files are passed for other validations to pass
        form = Step4NoAccountForm(data=form_data, files={
            'international_license_photo': self.dummy_int_license,
            'passport_photo': self.dummy_passport
        }, temp_booking=self.temp_booking_future_return)
        self.assertFalse(form.is_valid())
        self.assertIn('passport_expiry_date', form.errors)
        self.assertIn("Your passport must not expire before the end of your booking.", form.errors['passport_expiry_date'])

