from django.test import TestCase
from datetime import date
import datetime
from django.db import models
from django.db.models.fields.files import FieldFile

from inventory.models import SalesProfile

from ..test_helpers.model_factories import (
    SalesProfileFactory,
    UserFactory,
)


class SalesProfileModelTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.sales_profile_with_user = SalesProfileFactory(user=cls.user)
        cls.sales_profile_no_user = SalesProfileFactory(user=None)

    def test_sales_profile_creation(self):
        self.assertIsInstance(self.sales_profile_with_user, SalesProfile)
        self.assertIsNotNone(self.sales_profile_with_user.pk)
        self.assertIsInstance(self.sales_profile_no_user, SalesProfile)
        self.assertIsNotNone(self.sales_profile_no_user.pk)
        self.assertEqual(SalesProfile.objects.count(), 2)

    def test_user_one_to_one_field(self):
        field = self.sales_profile_with_user._meta.get_field("user")
        self.assertEqual(field.related_model, self.user.__class__)
        self.assertEqual(field.remote_field.on_delete, models.CASCADE)
        self.assertTrue(field.null)
        self.assertTrue(field.blank)
        self.assertEqual(self.sales_profile_with_user.user, self.user)
        self.assertIsNone(self.sales_profile_no_user.user)
        self.assertEqual(field.help_text, "Optional link to a registered user account.")

    def test_name_field(self):
        field = self.sales_profile_with_user._meta.get_field("name")
        self.assertIsInstance(self.sales_profile_with_user.name, str)
        self.assertEqual(field.max_length, 100)
        self.assertFalse(field.blank)
        self.assertFalse(field.null)
        self.assertEqual(field.help_text, "Full name of the customer.")

    def test_email_field(self):
        field = self.sales_profile_with_user._meta.get_field("email")
        self.assertIsInstance(self.sales_profile_with_user.email, str)
        self.assertFalse(field.blank)
        self.assertFalse(field.null)
        self.assertEqual(field.help_text, "Email address of the customer.")

    def test_phone_number_field(self):
        field = self.sales_profile_with_user._meta.get_field("phone_number")
        self.assertIsInstance(self.sales_profile_with_user.phone_number, str)
        self.assertEqual(field.max_length, 20)
        self.assertFalse(field.blank)
        self.assertFalse(field.null)
        self.assertEqual(field.help_text, "Phone number of the customer.")

    def test_address_information_fields(self):
        profile = self.sales_profile_with_user
        address_fields = [
            "address_line_1",
            "address_line_2",
            "city",
            "state",
            "post_code",
            "country",
        ]
        for field_name in address_fields:
            field = profile._meta.get_field(field_name)
            self.assertIsInstance(getattr(profile, field_name), (str, type(None)))
            self.assertTrue(field.blank)
            self.assertTrue(field.null)
            self.assertIsNotNone(field.help_text)

    def test_drivers_license_image_field(self):
        field = self.sales_profile_with_user._meta.get_field("drivers_license_image")

        self.assertIsInstance(
            self.sales_profile_with_user.drivers_license_image, (FieldFile, type(None))
        )
        self.assertTrue(field.blank)
        self.assertTrue(field.null)
        self.assertEqual(field.upload_to, "drivers_licenses/")
        self.assertEqual(field.help_text, "Image of the customer's driver's license.")

    def test_drivers_license_number_field(self):
        field = self.sales_profile_with_user._meta.get_field("drivers_license_number")
        self.assertIsInstance(
            self.sales_profile_with_user.drivers_license_number, (str, type(None))
        )
        self.assertEqual(field.max_length, 50)
        self.assertTrue(field.blank)
        self.assertTrue(field.null)
        self.assertEqual(field.help_text, "Customer's driver's license number.")

    def test_drivers_license_expiry_field(self):
        field = self.sales_profile_with_user._meta.get_field("drivers_license_expiry")
        self.assertIsInstance(
            self.sales_profile_with_user.drivers_license_expiry, (date, type(None))
        )
        self.assertTrue(field.blank)
        self.assertTrue(field.null)
        self.assertEqual(
            field.help_text, "Expiration date of the customer's driver's license."
        )

    def test_date_of_birth_field(self):
        field = self.sales_profile_with_user._meta.get_field("date_of_birth")
        self.assertIsInstance(
            self.sales_profile_with_user.date_of_birth, (date, type(None))
        )
        self.assertTrue(field.blank)
        self.assertTrue(field.null)
        self.assertEqual(field.help_text, "Customer's date of birth.")

    def test_created_at_field(self):
        field = self.sales_profile_with_user._meta.get_field("created_at")
        self.assertIsInstance(
            self.sales_profile_with_user.created_at, datetime.datetime
        )
        self.assertTrue(field.auto_now_add)
        self.assertEqual(
            field.help_text, "The date and time when this sales profile was created."
        )

    def test_updated_at_field(self):
        field = self.sales_profile_with_user._meta.get_field("updated_at")
        self.assertIsInstance(
            self.sales_profile_with_user.updated_at, datetime.datetime
        )
        self.assertTrue(field.auto_now)
        self.assertEqual(
            field.help_text,
            "The date and time when this sales profile was last updated.",
        )

        old_updated_at = self.sales_profile_with_user.updated_at
        self.sales_profile_with_user.name = "Updated Name"
        self.sales_profile_with_user.save()
        self.assertGreater(self.sales_profile_with_user.updated_at, old_updated_at)

    def test_str_method(self):
        self.assertEqual(
            str(self.sales_profile_with_user),
            f"Sales Profile for {self.user.get_username()} ({self.sales_profile_with_user.name})",
        )
        self.assertEqual(
            str(self.sales_profile_no_user),
            f"Sales Profile for {self.sales_profile_no_user.name} ({self.sales_profile_no_user.email})",
        )

    def test_meta_options(self):
        self.assertEqual(SalesProfile._meta.verbose_name, "Sales Profile")
        self.assertEqual(SalesProfile._meta.verbose_name_plural, "Sales Profiles")
        self.assertEqual(SalesProfile._meta.ordering, ["name"])
