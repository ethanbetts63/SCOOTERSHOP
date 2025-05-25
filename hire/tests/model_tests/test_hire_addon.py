# hire/tests/model_tests/hire_addon_tests.py

from decimal import Decimal
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db import IntegrityError

# Import model factory
from hire.tests.test_helpers.model_factories import create_addon
# Import the AddOn model directly to test its defaults
from hire.models import AddOn


class AddOnModelTest(TestCase):
    """
    Unit tests for the AddOn model.
    """

    def test_create_basic_addon(self):
        """
        Test that a basic AddOn instance can be created.
        """
        addon = create_addon(
            name="GPS Device",
            description="Portable GPS navigation system.",
            cost=Decimal('12.50'),
            min_quantity=1,
            max_quantity=3,
            is_available=True
        )
        self.assertIsNotNone(addon.pk)
        self.assertEqual(addon.name, "GPS Device")
        self.assertEqual(addon.description, "Portable GPS navigation system.")
        self.assertEqual(addon.cost, Decimal('12.50'))
        self.assertEqual(addon.min_quantity, 1)
        self.assertEqual(addon.max_quantity, 3)
        self.assertTrue(addon.is_available)
        self.assertIsNotNone(addon.created_at)
        self.assertIsNotNone(addon.updated_at)

    def test_str_method(self):
        """
        Test the __str__ method of AddOn.
        """
        addon = create_addon(name="Riding Jacket")
        self.assertEqual(str(addon), "Riding Jacket")

    # --- clean() method tests ---

    def test_clean_negative_cost_raises_error(self):
        """
        Test that clean() raises ValidationError if cost is negative.
        """
        addon = create_addon(name="Invalid AddOn", cost=Decimal('-5.00'))
        with self.assertRaises(ValidationError) as cm:
            addon.clean()
        self.assertIn('cost', cm.exception.message_dict)
        self.assertEqual(cm.exception.message_dict['cost'][0], "Add-on cost cannot be negative.")

    def test_clean_min_quantity_less_than_one_raises_error(self):
        """
        Test that clean() raises ValidationError if min_quantity is less than 1.
        """
        addon = create_addon(name="Invalid AddOn", min_quantity=0)
        with self.assertRaises(ValidationError) as cm:
            addon.clean()
        self.assertIn('min_quantity', cm.exception.message_dict)
        self.assertEqual(cm.exception.message_dict['min_quantity'][0], "Minimum quantity must be at least 1.")

    def test_clean_max_quantity_less_than_min_quantity_raises_error(self):
        """
        Test that clean() raises ValidationError if max_quantity is less than min_quantity.
        """
        addon = create_addon(name="Invalid AddOn", min_quantity=5, max_quantity=3)
        with self.assertRaises(ValidationError) as cm:
            addon.clean()
        self.assertIn('max_quantity', cm.exception.message_dict)
        self.assertEqual(cm.exception.message_dict['max_quantity'][0], "Maximum quantity cannot be less than minimum quantity.")

    def test_clean_valid_addon_passes(self):
        """
        Test that a valid AddOn instance passes clean() without errors.
        """
        addon = create_addon(
            name="Valid AddOn",
            cost=Decimal('25.00'),
            min_quantity=1,
            max_quantity=10,
            is_available=False # Availability doesn't affect clean() for AddOn itself
        )
        try:
            addon.clean()
        except ValidationError:
            self.fail("ValidationError raised unexpectedly for a valid AddOn.")

    def test_default_quantity_values(self):
        """
        Test that min_quantity and max_quantity default to 1 as per the model definition.
        We create the object directly here to bypass factory defaults.
        """
        addon = AddOn.objects.create(name="Default Quantity AddOn", cost=Decimal('5.00'))
        self.assertEqual(addon.min_quantity, 1)
        self.assertEqual(addon.max_quantity, 1)

