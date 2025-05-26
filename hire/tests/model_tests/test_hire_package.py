# hire/tests/model_tests/test_hire_packages.py

from decimal import Decimal
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db import IntegrityError

# Import model factories
from hire.tests.test_helpers.model_factories import create_package, create_addon
# Import the Package model directly for specific tests if needed
from hire.models import Package, AddOn


class PackageModelTest(TestCase):
    """
    Unit tests for the Package model.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up non-modified objects used by all test methods.
        """
        cls.addon1 = create_addon(name="GPS Device", daily_cost=Decimal('15.00'))
        cls.addon2 = create_addon(name="Riding Jacket", daily_cost=Decimal('25.00'))

    def test_create_basic_package(self):
        """
        Test that a basic Package instance can be created.
        """
        package = create_package(
            name="Weekend Warrior",
            description="A package for weekend adventures.",
            daily_cost=Decimal('150.00'), # Using daily_cost as per Package model update
            is_available=True
        )
        self.assertIsNotNone(package.pk)
        self.assertEqual(package.name, "Weekend Warrior")
        self.assertEqual(package.description, "A package for weekend adventures.")
        self.assertEqual(package.daily_cost, Decimal('150.00')) # Assert against the new field name
        self.assertTrue(package.is_available)
        self.assertIsNotNone(package.created_at)
        self.assertIsNotNone(package.updated_at)

    def test_str_method(self):
        """
        Test the __str__ method of Package.
        """
        package = create_package(name="City Explorer Pack")
        self.assertEqual(str(package), "City Explorer Pack")

    def test_add_ons_relationship(self):
        """
        Test the Many-to-Many relationship with AddOn.
        """
        package = create_package(
            name="Adventure Bundle",
            daily_cost=Decimal('100.00'), # Using daily_cost
            add_ons=[self.addon1, self.addon2]
        )
        self.assertEqual(package.add_ons.count(), 2)
        self.assertIn(self.addon1, package.add_ons.all())
        self.assertIn(self.addon2, package.add_ons.all())

        # Test adding an add-on after creation
        addon3 = create_addon(name="Gloves", daily_cost=Decimal('10.00')) # Using daily_cost
        package.add_ons.add(addon3)
        self.assertEqual(package.add_ons.count(), 3)
        self.assertIn(addon3, package.add_ons.all())

    def test_add_ons_blank_default(self):
        """
        Test that a package can be created without any add-ons.
        """
        package = create_package(
            name="Basic Package",
            daily_cost=Decimal('50.00'), # Using daily_cost
            add_ons=None # Explicitly pass None or omit for default blank
        )
        self.assertEqual(package.add_ons.count(), 0)

    # --- clean() method tests ---

    def test_clean_negative_package_price_raises_error(self):
        """
        Test that clean() raises ValidationError if package_price is negative.
        """
        # Using daily_cost as per Package model update
        package = create_package(name="Invalid Price Package", daily_cost=Decimal('-10.00'))
        with self.assertRaises(ValidationError) as cm:
            package.clean()
        self.assertIn('daily_cost', cm.exception.message_dict)
        # Updated assertion message to match the actual error from the model
        self.assertEqual(cm.exception.message_dict['daily_cost'][0], "Package daily cost cannot be negative.")

    def test_clean_valid_package_passes(self):
        """
        Test that a valid Package instance passes clean() without errors.
        """
        package = create_package(
            name="Valid Package",
            daily_cost=Decimal('75.00'), # Using daily_cost
            add_ons=[self.addon1],
            is_available=False # Availability doesn't affect clean() for Package itself
        )
        try:
            package.clean()
        except ValidationError:
            self.fail("ValidationError raised unexpectedly for a valid Package.")
