# hire/tests/model_tests/test_driver_profile.py

import datetime
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
#from unittest import mock # For mocking timezone.now() - Not currently used directly in failing tests
from dateutil.relativedelta import relativedelta # For precise date calculations

# Import model factories
from hire.tests.test_helpers.model_factories import create_driver_profile, create_user, create_hire_settings
# Import the DriverProfile model directly for specific tests if needed
from hire.models import DriverProfile
from dashboard.models import HireSettings # To directly manipulate settings


class DriverProfileModelTest(TestCase):
    """
    Unit tests for the DriverProfile model.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up non-modified objects used by all test methods.
        """
        # Create a default HireSettings instance for age validation
        cls.hire_settings = create_hire_settings(minimum_driver_age=21)
        cls.user = create_user(username="testuser")

    def test_create_basic_driver_profile(self):
        """
        Test that a basic DriverProfile instance can be created.
        """
        driver_profile = create_driver_profile(
            name="Jane Doe",
            email="jane.doe@example.com",
            phone_number="0412345678",
            address_line_1="456 Oak Ave",
            city="Melbourne",
            country="Australia",
            date_of_birth=datetime.date(2000, 1, 1), # Over 21
            is_australian_resident=True,
            license_number="AUS987654",
            license_expiry_date=timezone.now().date() + datetime.timedelta(days=365),
            license_photo="dummy/path/license.jpg" # Added for basic creation
        )
        self.assertIsNotNone(driver_profile.pk)
        self.assertEqual(driver_profile.name, "Jane Doe")
        self.assertEqual(driver_profile.email, "jane.doe@example.com")
        self.assertTrue(driver_profile.is_australian_resident)
        self.assertIsNotNone(driver_profile.created_at)
        self.assertIsNotNone(driver_profile.updated_at)

    def test_str_method_with_user(self):
        """
        Test the __str__ method when linked to a User.
        """
        driver_profile = create_driver_profile(user=self.user, license_photo="dummy/path/license.jpg") # Added license_photo
        self.assertEqual(str(driver_profile), str(self.user))

    def test_str_method_without_user(self):
        """
        Test the __str__ method when not linked to a User, using name/email.
        """
        driver_profile = create_driver_profile(user=None, name="Anonymous Driver", email="anon@example.com", license_photo="dummy/path/license.jpg") # Added license_photo
        self.assertEqual(str(driver_profile), "Anonymous Driver")

        driver_profile_no_name_email = create_driver_profile(
            user=None,
            name="",
            email="",
            phone_number="0498765432",
            address_line_1="1 Street",
            city="City",
            country="Country",
            date_of_birth=datetime.date(1990,1,1),
            license_expiry_date=datetime.date(2030,1,1),
            license_photo="dummy/path/license.jpg" # Added license_photo
        )
        self.assertEqual(str(driver_profile_no_name_email), "0498765432")

    # --- clean() method tests ---

    def test_clean_driver_under_minimum_age_raises_error(self):
        """
        Test that clean() raises ValidationError if driver is under minimum age.
        """
        self.hire_settings.minimum_driver_age = 21
        self.hire_settings.save()

        # Driver is 20 years old
        date_of_birth = timezone.now().date() - relativedelta(years=20)
        driver_profile = create_driver_profile(
            date_of_birth=date_of_birth,
            license_photo="dummy/path/license.jpg" # Australian resident needs this
        )

        with self.assertRaises(ValidationError) as cm:
            driver_profile.clean()
        self.assertIn('date_of_birth', cm.exception.message_dict)
        self.assertEqual(
            cm.exception.message_dict['date_of_birth'][0],
            "Driver must be at least 21 years old."
        )

    def test_clean_driver_at_minimum_age_passes(self):
        """
        Test that clean() passes if driver is exactly at minimum age.
        """
        self.hire_settings.minimum_driver_age = 21
        self.hire_settings.save()

        # Driver is exactly 21 years old
        date_of_birth = timezone.now().date() - relativedelta(years=21)
        driver_profile = create_driver_profile(
            date_of_birth=date_of_birth,
            is_australian_resident=True, # Explicitly an Australian resident
            license_photo="path/to/valid_license.jpg", # Provide required license photo
            license_number="VALID123",
            license_expiry_date=timezone.now().date() + datetime.timedelta(days=365)
        )
        try:
            driver_profile.clean()
        except ValidationError as e:
            self.fail(f"ValidationError raised unexpectedly for driver exactly at minimum age: {e.message_dict}")

    # --- Australian Resident Specific Validations ---

    def test_clean_australian_resident_missing_license_photo_raises_error(self):
        """
        Test that clean() raises ValidationError for Australian resident missing license photo.
        """
        driver_profile = create_driver_profile(
            is_australian_resident=True,
            license_photo=None # Missing
        )
        with self.assertRaises(ValidationError) as cm:
            driver_profile.clean()
        self.assertIn('license_photo', cm.exception.message_dict)
        self.assertEqual(
            cm.exception.message_dict['license_photo'][0],
            "Australian residents must upload their domestic driver's license photo."
        )

    def test_clean_australian_resident_missing_license_number_raises_error(self):
        """
        Test that clean() raises ValidationError for Australian resident missing license number.
        """
        driver_profile = create_driver_profile(
            is_australian_resident=True,
            license_number="", # Missing
            license_photo="dummy/path/license.jpg"
        )
        with self.assertRaises(ValidationError) as cm:
            driver_profile.clean()
        self.assertIn('license_number', cm.exception.message_dict)
        self.assertEqual(
            cm.exception.message_dict['license_number'][0],
            "Australian residents must provide their domestic license number."
        )

    def test_clean_australian_resident_expired_license_raises_error(self):
        """
        Test that clean() raises ValidationError for Australian resident with expired license.
        """
        driver_profile = create_driver_profile(
            is_australian_resident=True,
            license_expiry_date=timezone.now().date() - datetime.timedelta(days=1), # Expired yesterday
            license_photo="dummy/path/license.jpg",
            license_number="EXPIREDLIC"
        )
        with self.assertRaises(ValidationError) as cm:
            driver_profile.clean()
        self.assertIn('license_expiry_date', cm.exception.message_dict)
        self.assertEqual(
            cm.exception.message_dict['license_expiry_date'][0],
            "Australian domestic driver's license must not be expired."
        )

    def test_clean_australian_resident_with_international_license_details_raises_error(self):
        """
        Test that clean() raises ValidationError for Australian resident having international license details.
        """
        driver_profile = create_driver_profile(
            is_australian_resident=True,
            international_license_expiry_date=timezone.now().date() + datetime.timedelta(days=100),
            international_license_issuing_country="USA",
            license_photo="dummy/path/license.jpg", # Needs this
            license_number="AUSLIC1"
        )
        with self.assertRaises(ValidationError) as cm:
            driver_profile.clean()
        self.assertIn('international_license_expiry_date', cm.exception.message_dict)
        self.assertIn('international_license_issuing_country', cm.exception.message_dict)
        self.assertEqual(
            cm.exception.message_dict['international_license_expiry_date'][0],
            "International license expiry date should not be provided for Australian residents."
        )
        self.assertEqual(
            cm.exception.message_dict['international_license_issuing_country'][0],
            "International license issuing country should not be provided for Australian residents."
        )

    def test_clean_australian_resident_with_passport_details_raises_error(self):
        """
        Test that clean() raises ValidationError for Australian resident having passport details.
        """
        driver_profile = create_driver_profile(
            is_australian_resident=True,
            passport_photo="path/to/passport.jpg",
            passport_number="P1234567",
            passport_expiry_date=timezone.now().date() + datetime.timedelta(days=100),
            license_photo="dummy/path/license.jpg", # Needs this
            license_number="AUSLIC2"
        )
        with self.assertRaises(ValidationError) as cm:
            driver_profile.clean()
        self.assertIn('passport_photo', cm.exception.message_dict)
        self.assertIn('passport_number', cm.exception.message_dict)
        self.assertIn('passport_expiry_date', cm.exception.message_dict)
        self.assertEqual(
            cm.exception.message_dict['passport_photo'][0],
            "Passport photo should not be provided for Australian residents."
        )
        self.assertEqual(
            cm.exception.message_dict['passport_number'][0],
            "Passport number should not be provided for Australian residents."
        )
        self.assertEqual(
            cm.exception.message_dict['passport_expiry_date'][0],
            "Passport expiry date should not be provided for Australian residents."
        )

    # --- Foreigner Specific Validations ---

    def test_clean_foreigner_missing_international_license_photo_raises_error(self):
        """
        Test that clean() raises ValidationError for foreigner missing international license photo.
        """
        driver_profile = create_driver_profile(
            is_australian_resident=False,
            international_license_photo=None, # Missing
            passport_photo="dummy/path/passport.jpg", # Provide other required fields
            international_license_issuing_country="USA",
            international_license_expiry_date=timezone.now().date() + datetime.timedelta(days=365),
            passport_number="P123",
            passport_expiry_date=timezone.now().date() + datetime.timedelta(days=365)
        )
        with self.assertRaises(ValidationError) as cm:
            driver_profile.clean()
        self.assertIn('international_license_photo', cm.exception.message_dict)
        self.assertEqual(
            cm.exception.message_dict['international_license_photo'][0],
            "Foreign drivers must upload their International Driver's License photo."
        )

    def test_clean_foreigner_missing_passport_photo_raises_error(self):
        """
        Test that clean() raises ValidationError for foreigner missing passport photo.
        """
        driver_profile = create_driver_profile(
            is_australian_resident=False,
            passport_photo=None, # Missing
            international_license_photo="dummy/path/int_license.jpg", # Provide other required fields
            international_license_issuing_country="USA",
            international_license_expiry_date=timezone.now().date() + datetime.timedelta(days=365),
            passport_number="P123",
            passport_expiry_date=timezone.now().date() + datetime.timedelta(days=365)
        )
        with self.assertRaises(ValidationError) as cm:
            driver_profile.clean()
        self.assertIn('passport_photo', cm.exception.message_dict)
        self.assertEqual(
            cm.exception.message_dict['passport_photo'][0],
            "Foreign drivers must upload their passport photo."
        )

    def test_clean_foreigner_missing_international_license_country_raises_error(self):
        """
        Test that clean() raises ValidationError for foreigner missing international license issuing country.
        """
        driver_profile = create_driver_profile(
            is_australian_resident=False,
            international_license_issuing_country="", # Missing
            international_license_photo="dummy/path/int_license.jpg",
            passport_photo="dummy/path/passport.jpg",
            international_license_expiry_date=timezone.now().date() + datetime.timedelta(days=365),
            passport_number="P123",
            passport_expiry_date=timezone.now().date() + datetime.timedelta(days=365)
        )
        with self.assertRaises(ValidationError) as cm:
            driver_profile.clean()
        self.assertIn('international_license_issuing_country', cm.exception.message_dict)
        self.assertEqual(
            cm.exception.message_dict['international_license_issuing_country'][0],
            "Foreign drivers must provide the issuing country of their International Driver's License."
        )

    def test_clean_foreigner_expired_international_license_raises_error(self):
        """
        Test that clean() raises ValidationError for foreigner with expired international license.
        """
        driver_profile = create_driver_profile(
            is_australian_resident=False,
            international_license_expiry_date=timezone.now().date() - datetime.timedelta(days=1), # Expired
            international_license_photo="dummy/path/int_license.jpg",
            passport_photo="dummy/path/passport.jpg",
            international_license_issuing_country="USA",
            passport_number="P123",
            passport_expiry_date=timezone.now().date() + datetime.timedelta(days=365)
        )
        with self.assertRaises(ValidationError) as cm:
            driver_profile.clean()
        self.assertIn('international_license_expiry_date', cm.exception.message_dict)
        self.assertEqual(
            cm.exception.message_dict['international_license_expiry_date'][0],
            "International Driver's License must not be expired."
        )

    def test_clean_foreigner_missing_passport_number_raises_error(self):
        """
        Test that clean() raises ValidationError for foreigner missing passport number.
        """
        driver_profile = create_driver_profile(
            is_australian_resident=False,
            passport_number="", # Missing
            international_license_photo="dummy/path/int_license.jpg",
            passport_photo="dummy/path/passport.jpg",
            international_license_issuing_country="USA",
            international_license_expiry_date=timezone.now().date() + datetime.timedelta(days=365),
            passport_expiry_date=timezone.now().date() + datetime.timedelta(days=365)
        )
        with self.assertRaises(ValidationError) as cm:
            driver_profile.clean()
        self.assertIn('passport_number', cm.exception.message_dict)
        self.assertEqual(
            cm.exception.message_dict['passport_number'][0],
            "Foreign drivers must provide their passport number."
        )

    def test_clean_foreigner_missing_passport_expiry_date_raises_error(self):
        """
        Test that clean() raises ValidationError for foreigner missing passport expiry date.
        """
        driver_profile = create_driver_profile(
            is_australian_resident=False,
            passport_expiry_date=None, # Missing
            # Provide other required fields for a foreigner to isolate this error
            international_license_photo="path/to/int_license.jpg",
            international_license_issuing_country="Canada",
            international_license_expiry_date=timezone.now().date() + datetime.timedelta(days=365),
            passport_photo="path/to/passport.jpg",
            passport_number="CAN12345",
            _set_default_expiry_dates=False # Crucial: Prevent factory from setting a default
        )
        with self.assertRaises(ValidationError) as cm:
            driver_profile.clean()
        # Ensure the specific error for passport_expiry_date is present
        self.assertIn('passport_expiry_date', cm.exception.message_dict)
        self.assertEqual(
            cm.exception.message_dict['passport_expiry_date'][0],
            "Foreign drivers must provide their passport expiry date."
        )


    def test_clean_foreigner_expired_passport_raises_error(self):
        """
        Test that clean() raises ValidationError for foreigner with expired passport.
        """
        driver_profile = create_driver_profile(
            is_australian_resident=False,
            passport_expiry_date=timezone.now().date() - datetime.timedelta(days=1), # Expired
            international_license_photo="dummy/path/int_license.jpg",
            passport_photo="dummy/path/passport.jpg",
            international_license_issuing_country="USA",
            international_license_expiry_date=timezone.now().date() + datetime.timedelta(days=365),
            passport_number="P123"
        )
        with self.assertRaises(ValidationError) as cm:
            driver_profile.clean()
        self.assertIn('passport_expiry_date', cm.exception.message_dict)
        self.assertEqual(
            cm.exception.message_dict['passport_expiry_date'][0],
            "Passport must not be expired."
        )

    def test_clean_foreigner_with_australian_license_photo_raises_error(self):
        """
        Test that clean() raises ValidationError for foreigner having Australian domestic license photo.
        """
        driver_profile = create_driver_profile(
            is_australian_resident=False,
            license_photo="path/to/aus_license.jpg", # Should not be provided
            international_license_photo="dummy/path/int_license.jpg", # Provide other required fields
            passport_photo="dummy/path/passport.jpg",
            international_license_issuing_country="USA",
            international_license_expiry_date=timezone.now().date() + datetime.timedelta(days=365),
            passport_number="P123",
            passport_expiry_date=timezone.now().date() + datetime.timedelta(days=365)
        )
        with self.assertRaises(ValidationError) as cm:
            driver_profile.clean()
        self.assertIn('license_photo', cm.exception.message_dict)
        self.assertEqual(
            cm.exception.message_dict['license_photo'][0],
            "Australian domestic driver's license photo should not be provided for foreign drivers."
        )

    def test_clean_valid_australian_resident_profile_passes(self):
        """
        Test that a valid Australian resident DriverProfile passes clean() without errors.
        """
        driver_profile = create_driver_profile(
            is_australian_resident=True,
            license_photo="path/to/aus_license.jpg",
            license_number="AUS123456",
            license_expiry_date=timezone.now().date() + datetime.timedelta(days=365),
            date_of_birth=timezone.now().date() - relativedelta(years=25) # Ensure valid age
        )
        try:
            driver_profile.clean()
        except ValidationError as e:
            self.fail(f"ValidationError raised unexpectedly for a valid Australian resident profile: {e.message_dict}")

    def test_clean_valid_foreigner_profile_passes(self):
        """
        Test that a valid foreigner DriverProfile passes clean() without errors.
        """
        driver_profile = create_driver_profile(
            is_australian_resident=False,
            international_license_photo="path/to/int_license.jpg",
            international_license_issuing_country="USA",
            international_license_expiry_date=timezone.now().date() + datetime.timedelta(days=365),
            passport_photo="path/to/passport.jpg",
            passport_number="P1234567",
            passport_expiry_date=timezone.now().date() + datetime.timedelta(days=365),
            date_of_birth=timezone.now().date() - relativedelta(years=25) # Ensure valid age
        )
        try:
            driver_profile.clean()
        except ValidationError as e:
            self.fail(f"ValidationError raised unexpectedly for a valid foreigner profile: {e.message_dict}")

