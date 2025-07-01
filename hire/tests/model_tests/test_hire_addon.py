                                            

from decimal import Decimal
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db import IntegrityError

                      
from hire.tests.test_helpers.model_factories import create_addon
                                                      
from hire.models import AddOn


class AddOnModelTest(TestCase):
    """
    Unit tests for the AddOn model.
    """

    def test_create_basic_addon(self):
        """
        Test that a basic AddOn instance can be created.
        Updated to use hourly_cost and daily_cost.
        """
        addon = create_addon(
            name="GPS Device",
            description="Portable GPS navigation system.",
            hourly_cost=Decimal('2.50'),                       
            daily_cost=Decimal('12.50'),             
            min_quantity=1,
            max_quantity=3,
            is_available=True
        )
        self.assertIsNotNone(addon.pk)
        self.assertEqual(addon.name, "GPS Device")
        self.assertEqual(addon.description, "Portable GPS navigation system.")
        self.assertEqual(addon.hourly_cost, Decimal('2.50'))                   
        self.assertEqual(addon.daily_cost, Decimal('12.50'))                   
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

                                  

    def test_clean_negative_cost_raises_error(self):
        """
        Test that clean() raises ValidationError if hourly_cost or daily_cost is negative.
        Updated to use hourly_cost and daily_cost.
        """
        addon = create_addon(name="Invalid AddOn", hourly_cost=Decimal('-1.00'), daily_cost=Decimal('-5.00'))
        with self.assertRaises(ValidationError) as cm:
            addon.clean()
        self.assertIn('hourly_cost', cm.exception.message_dict)
        self.assertIn('daily_cost', cm.exception.message_dict)
        self.assertEqual(cm.exception.message_dict['hourly_cost'][0], "Add-on hourly cost cannot be negative.")
        self.assertEqual(cm.exception.message_dict['daily_cost'][0], "Add-on daily cost cannot be negative.")


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
        Updated to use hourly_cost and daily_cost.
        """
        addon = create_addon(
            name="Valid AddOn",
            hourly_cost=Decimal('5.00'),                       
            daily_cost=Decimal('25.00'),             
            min_quantity=1,
            max_quantity=10,
            is_available=False                                                       
        )
        try:
            addon.clean()
        except ValidationError:
            self.fail("ValidationError raised unexpectedly for a valid AddOn.")

    def test_default_quantity_values(self):
        """
        Test that min_quantity and max_quantity default to 1 as per the model definition.
        We create the object directly here to bypass factory defaults.
        Updated to use hourly_cost and daily_cost.
        """
        addon = AddOn.objects.create(name="Default Quantity AddOn", hourly_cost=Decimal('1.00'), daily_cost=Decimal('5.00'))
        self.assertEqual(addon.min_quantity, 1)
        self.assertEqual(addon.max_quantity, 1)

