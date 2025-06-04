from django.test import TestCase
from django.core.exceptions import ValidationError
from django.conf import settings
from datetime import datetime

# Import the ServiceProfile model
from service.models import ServiceProfile

# Import factories
from ..test_helpers.model_factories import ServiceProfileFactory, UserFactory

# Get the User model dynamically
User = settings.AUTH_USER_MODEL

class ServiceProfileModelTest(TestCase):
    """
    Tests for the ServiceProfile model.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up non-modified objects used by all test methods.
        We'll create a single ServiceProfile instance using the factory.
        """
        cls.service_profile = ServiceProfileFactory()

    def test_service_profile_creation(self):
        """
        Test that a ServiceProfile instance can be created successfully using the factory.
        """
        self.assertIsInstance(self.service_profile, ServiceProfile)
        self.assertIsNotNone(self.service_profile.pk) # Check if it has a primary key (saved to DB)

    def test_user_relationship(self):
        """
        Test the OneToOneField relationship with the User model.
        """
        profile = self.service_profile
        self.assertIsNotNone(profile.user)
        self.assertIsInstance(profile.user, UserFactory._meta.model) # Check if it's an instance of the User model
        self.assertEqual(profile.user.service_profile, profile) # Check reverse relationship

        # Test creating a profile without a user (should be possible as null=True)
        profile_no_user = ServiceProfileFactory(user=None, name="Guest User", email="guest@example.com", phone_number="1234567890", address_line_1="123 Guest St", city="Guestville", post_code="12345", country="AU")
        self.assertIsNone(profile_no_user.user)

    def test_contact_information_fields(self):
        """
        Test the 'name', 'email', and 'phone_number' fields.
        """
        profile = self.service_profile
        self.assertEqual(profile._meta.get_field('name').max_length, 100)
        self.assertFalse(profile._meta.get_field('name').blank)
        self.assertFalse(profile._meta.get_field('name').null)
        self.assertIsInstance(profile.name, str)

        self.assertFalse(profile._meta.get_field('email').blank)
        self.assertFalse(profile._meta.get_field('email').null)
        self.assertIsInstance(profile.email, str)
        self.assertIn('@', profile.email) # Basic email format check

        self.assertEqual(profile._meta.get_field('phone_number').max_length, 20)
        self.assertFalse(profile._meta.get_field('phone_number').blank)
        self.assertFalse(profile._meta.get_field('phone_number').null)
        self.assertIsInstance(profile.phone_number, str)

    def test_address_information_fields(self):
        """
        Test the address fields.
        """
        profile = self.service_profile
        self.assertEqual(profile._meta.get_field('address_line_1').max_length, 100)
        self.assertFalse(profile._meta.get_field('address_line_1').blank)
        self.assertFalse(profile._meta.get_field('address_line_1').null)
        self.assertIsInstance(profile.address_line_1, str)

        self.assertEqual(profile._meta.get_field('address_line_2').max_length, 100)
        self.assertTrue(profile._meta.get_field('address_line_2').blank)
        self.assertTrue(profile._meta.get_field('address_line_2').null)
        # Can be None or string

        self.assertEqual(profile._meta.get_field('city').max_length, 50)
        self.assertFalse(profile._meta.get_field('city').blank)
        self.assertFalse(profile._meta.get_field('city').null)
        self.assertIsInstance(profile.city, str)

        self.assertEqual(profile._meta.get_field('state').max_length, 50)
        self.assertTrue(profile._meta.get_field('state').blank)
        self.assertTrue(profile._meta.get_field('state').null)
        # Can be None or string

        self.assertEqual(profile._meta.get_field('post_code').max_length, 20)
        self.assertFalse(profile._meta.get_field('post_code').blank)
        self.assertFalse(profile._meta.get_field('post_code').null)
        self.assertIsInstance(profile.post_code, str)

        self.assertEqual(profile._meta.get_field('country').max_length, 50)
        self.assertFalse(profile._meta.get_field('country').blank)
        self.assertFalse(profile._meta.get_field('country').null)
        self.assertIsInstance(profile.country, str)

    def test_timestamps(self):
        """
        Test 'created_at' and 'updated_at' fields.
        """
        profile = self.service_profile
        self.assertIsInstance(profile.created_at, datetime)
        self.assertIsInstance(profile.updated_at, datetime)
        self.assertLessEqual(profile.created_at, profile.updated_at)

        # Test auto_now for updated_at
        old_updated_at = profile.updated_at
        profile.name = "New Name"
        profile.save()
        self.assertGreater(profile.updated_at, old_updated_at)

    def test_clean_method_phone_number_validation(self):
        """
        Test the clean method's validation for the 'phone_number' field.
        """
        # Create a fresh instance for this test to ensure a controlled starting state
        # The factory now generates valid phone numbers, so we start with one.
        profile = ServiceProfileFactory()

        # Test valid phone numbers (should pass with the new regex)
        profile.phone_number = "0412345678"
        profile.full_clean() # Should not raise error

        profile.phone_number = "02 1234 5678"
        profile.full_clean() # Should not raise error

        profile.phone_number = "+61-412-345-678"
        profile.full_clean() # Should not raise error

        # Define the expected error message for invalid phone numbers
        expected_error_message = "Phone number must contain only digits, spaces, hyphens, and an optional leading '+'. Example: '+61412345678' or '0412 345 678'."

        # Test invalid phone numbers (non-digit characters other than space/hyphen/plus)
        profile.phone_number = "041234567A"
        with self.assertRaisesMessage(ValidationError, expected_error_message):
            profile.full_clean()

        profile.phone_number = "04123(456)78"
        with self.assertRaisesMessage(ValidationError, expected_error_message):
            profile.full_clean()

    def test_clean_method_email_user_email_discrepancy(self):
        """
        Test the clean method's behavior when service_profile.email
        and user.email are different.
        """
        user = UserFactory(email="user@example.com")
        # Ensure the profile created here also has a valid phone number from the factory
        profile = ServiceProfileFactory(user=user, email="profile@example.com")

        # As per the current clean method, it should not raise a ValidationError
        # It has a 'pass' statement for this scenario.
        try:
            profile.full_clean()
        except ValidationError as e:
            self.fail(f"ValidationError unexpectedly raised for email discrepancy: {e.message_dict}")

        # Test with no user associated, email should still validate
        profile_no_user = ServiceProfileFactory(user=None, email="another@example.com")
        try:
            profile_no_user.full_clean()
        except ValidationError as e:
            self.fail(f"ValidationError unexpectedly raised for no user email: {e.message_dict}")


    def test_str_method(self):
        """
        Test the __str__ method of the ServiceProfile model.
        It should return a descriptive string based on user or name/email.
        """
        # Test with a user linked
        profile_with_user = self.service_profile
        expected_str_with_user = f"Profile for {profile_with_user.user.get_username()} ({profile_with_user.name})"
        self.assertEqual(str(profile_with_user), expected_str_with_user)

        # Test without a user linked
        profile_no_user = ServiceProfileFactory(user=None, name="Guest Customer", email="guest@example.com", phone_number="123", address_line_1="123 Main", city="Anytown", post_code="12345", country="AU")
        expected_str_no_user = f"Profile for {profile_no_user.name} ({profile_no_user.email})"
        self.assertEqual(str(profile_no_user), expected_str_no_user)

    def test_meta_options(self):
        """
        Test the Meta options of the ServiceProfile model.
        """
        self.assertEqual(ServiceProfile._meta.verbose_name, "Service Customer Profile")
        self.assertEqual(ServiceProfile._meta.verbose_name_plural, "Service Customer Profiles")
