from django.test import TestCase
from django.core.exceptions import ValidationError
from django.conf import settings
from datetime import datetime


from service.models import ServiceProfile


from users.tests.test_helpers.model_factories import UserFactory
from service.tests.test_helpers.model_factories import ServiceProfileFactory

User = settings.AUTH_USER_MODEL


class ServiceProfileModelTest(TestCase):

    @classmethod
    def setUpTestData(cls):

        cls.service_profile = ServiceProfileFactory()

    def test_service_profile_creation(self):

        self.assertIsInstance(self.service_profile, ServiceProfile)
        self.assertIsNotNone(self.service_profile.pk)

    def test_user_relationship(self):

        profile = self.service_profile
        self.assertIsNotNone(profile.user)
        self.assertIsInstance(profile.user, UserFactory._meta.model)
        self.assertEqual(profile.user.service_profile, profile)

        profile_no_user = ServiceProfileFactory(
            user=None,
            name="Guest User",
            email="guest@example.com",
            phone_number="1234567890",
            address_line_1="123 Guest St",
            city="Guestville",
            post_code="12345",
            country="AU",
        )
        self.assertIsNone(profile_no_user.user)

    def test_contact_information_fields(self):

        profile = self.service_profile
        self.assertEqual(profile._meta.get_field("name").max_length, 100)
        self.assertFalse(profile._meta.get_field("name").blank)
        self.assertFalse(profile._meta.get_field("name").null)
        self.assertIsInstance(profile.name, str)

        self.assertFalse(profile._meta.get_field("email").blank)
        self.assertFalse(profile._meta.get_field("email").null)
        self.assertIsInstance(profile.email, str)
        self.assertIn("@", profile.email)

        self.assertEqual(profile._meta.get_field("phone_number").max_length, 20)
        self.assertFalse(profile._meta.get_field("phone_number").blank)
        self.assertFalse(profile._meta.get_field("phone_number").null)
        self.assertIsInstance(profile.phone_number, str)

    def test_address_information_fields(self):

        profile = self.service_profile
        self.assertEqual(profile._meta.get_field("address_line_1").max_length, 100)
        self.assertFalse(profile._meta.get_field("address_line_1").blank)
        self.assertFalse(profile._meta.get_field("address_line_1").null)
        self.assertIsInstance(profile.address_line_1, str)

        self.assertEqual(profile._meta.get_field("address_line_2").max_length, 100)
        self.assertTrue(profile._meta.get_field("address_line_2").blank)
        self.assertTrue(profile._meta.get_field("address_line_2").null)

        self.assertEqual(profile._meta.get_field("city").max_length, 50)
        self.assertFalse(profile._meta.get_field("city").blank)
        self.assertFalse(profile._meta.get_field("city").null)
        self.assertIsInstance(profile.city, str)

        self.assertEqual(profile._meta.get_field("state").max_length, 50)
        self.assertTrue(profile._meta.get_field("state").blank)
        self.assertTrue(profile._meta.get_field("state").null)

        self.assertEqual(profile._meta.get_field("post_code").max_length, 20)
        self.assertFalse(profile._meta.get_field("post_code").blank)
        self.assertFalse(profile._meta.get_field("post_code").null)
        self.assertIsInstance(profile.post_code, str)

        self.assertEqual(profile._meta.get_field("country").max_length, 50)
        self.assertFalse(profile._meta.get_field("country").blank)
        self.assertFalse(profile._meta.get_field("country").null)
        self.assertIsInstance(profile.country, str)

    def test_timestamps(self):

        profile = self.service_profile
        self.assertIsInstance(profile.created_at, datetime)
        self.assertIsInstance(profile.updated_at, datetime)
        self.assertLessEqual(profile.created_at, profile.updated_at)

        old_updated_at = profile.updated_at
        profile.name = "New Name"
        profile.save()
        self.assertGreater(profile.updated_at, old_updated_at)

    def test_clean_method_phone_number_validation(self):

        profile = ServiceProfileFactory()

        profile.phone_number = "0412345678"
        profile.full_clean()

        profile.phone_number = "02 1234 5678"
        profile.full_clean()

        profile.phone_number = "+61-412-345-678"
        profile.full_clean()

        expected_error_message = "Phone number must contain only digits, spaces, hyphens, and an optional leading '+'. Example: '+61412345678' or '0412 345 678'."

        profile.phone_number = "041234567A"
        with self.assertRaisesMessage(ValidationError, expected_error_message):
            profile.full_clean()

        profile.phone_number = "04123(456)78"
        with self.assertRaisesMessage(ValidationError, expected_error_message):
            profile.full_clean()

    def test_clean_method_email_user_email_discrepancy(self):

        user = UserFactory(email="user@example.com")

        profile = ServiceProfileFactory(user=user, email="profile@example.com")

        try:
            profile.full_clean()
        except ValidationError as e:
            self.fail(
                f"ValidationError unexpectedly raised for email discrepancy: {e.message_dict}"
            )

        profile_no_user = ServiceProfileFactory(user=None, email="another@example.com")
        try:
            profile_no_user.full_clean()
        except ValidationError as e:
            self.fail(
                f"ValidationError unexpectedly raised for no user email: {e.message_dict}"
            )

    def test_str_method(self):

        profile_with_user = self.service_profile
        expected_str_with_user = f"Profile for {profile_with_user.user.get_username()} ({profile_with_user.name})"
        self.assertEqual(str(profile_with_user), expected_str_with_user)

        profile_no_user = ServiceProfileFactory(
            user=None,
            name="Guest Customer",
            email="guest@example.com",
            phone_number="123",
            address_line_1="123 Main",
            city="Anytown",
            post_code="12345",
            country="AU",
        )
        expected_str_no_user = (
            f"Profile for {profile_no_user.name} ({profile_no_user.email})"
        )
        self.assertEqual(str(profile_no_user), expected_str_no_user)

    def test_meta_options(self):

        self.assertEqual(ServiceProfile._meta.verbose_name, "Service Customer Profile")
        self.assertEqual(
            ServiceProfile._meta.verbose_name_plural, "Service Customer Profiles"
        )
