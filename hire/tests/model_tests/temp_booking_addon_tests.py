# hire/tests/model_tests/temp_booking_addon_tests.py

from decimal import Decimal
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db import IntegrityError

# Import model factories
from hire.tests.test_helpers.model_factories import (
    create_temp_hire_booking,
    create_addon,
    create_temp_booking_addon,
    create_motorcycle,
    create_driver_profile,
)

# Import the model directly to bypass factory defaults for specific tests
from hire.models import TempBookingAddOn


class TempBookingAddOnModelTest(TestCase):
    """
    Unit tests for the TempBookingAddOn model.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up non-modified objects used by all test methods.
        """
        cls.motorcycle = create_motorcycle()
        cls.driver_profile = create_driver_profile()
        cls.temp_booking = create_temp_hire_booking(
            motorcycle=cls.motorcycle,
            driver_profile=cls.driver_profile,
            grand_total=Decimal('100.00')
        )
        cls.addon_min1_max5 = create_addon(name="AddOn A", cost=Decimal('10.00'), min_quantity=1, max_quantity=5)
        cls.addon_min2_max2 = create_addon(name="AddOn B", cost=Decimal('25.00'), min_quantity=2, max_quantity=2)

    def test_create_basic_temp_booking_addon(self):
        """
        Test that a basic TempBookingAddOn instance can be created.
        """
        temp_booking_addon = create_temp_booking_addon(
            temp_booking=self.temp_booking,
            addon=self.addon_min1_max5,
            quantity=2,
            booked_addon_price=Decimal('10.00')
        )
        self.assertIsNotNone(temp_booking_addon.pk)
        self.assertEqual(temp_booking_addon.temp_booking, self.temp_booking)
        self.assertEqual(temp_booking_addon.addon, self.addon_min1_max5)
        self.assertEqual(temp_booking_addon.quantity, 2)
        self.assertEqual(temp_booking_addon.booked_addon_price, Decimal('10.00'))

    def test_str_method(self):
        """
        Test the __str__ method of TempBookingAddOn.
        """
        temp_booking_addon = create_temp_booking_addon(
            temp_booking=self.temp_booking,
            addon=self.addon_min1_max5,
            quantity=3
        )
        expected_str = f"3 x {self.addon_min1_max5.name} for Temp Booking {str(self.temp_booking.session_uuid)[:8]}"
        self.assertEqual(str(temp_booking_addon), expected_str)

        # Test with a deleted addon (addon=None) by creating the instance directly
        temp_booking_addon_deleted = TempBookingAddOn.objects.create(
            temp_booking=self.temp_booking,
            addon=None, # Explicitly set to None
            quantity=1,
            booked_addon_price=Decimal('10.00') # Price can be anything if addon is null
        )
        expected_str_deleted = f"1 x Deleted Add-On for Temp Booking {str(self.temp_booking.session_uuid)[:8]}"
        self.assertEqual(str(temp_booking_addon_deleted), expected_str_deleted)


    def test_unique_together_constraint(self):
        """
        Test that unique_together constraint (temp_booking, addon) prevents duplicates.
        """
        create_temp_booking_addon(
            temp_booking=self.temp_booking,
            addon=self.addon_min1_max5,
            quantity=1
        )
        with self.assertRaises(IntegrityError):
            create_temp_booking_addon(
                temp_booking=self.temp_booking,
                addon=self.addon_min1_max5, # Same addon for same temp booking
                quantity=2 # Quantity doesn't matter for uniqueness
            )

    # --- clean() method tests ---

    def test_clean_quantity_less_than_min_quantity_raises_error(self):
        """
        Test that clean() raises ValidationError if quantity is less than addon's min_quantity.
        """
        temp_booking_addon = create_temp_booking_addon(
            temp_booking=self.temp_booking,
            addon=self.addon_min2_max2, # min_quantity is 2
            quantity=1 # Invalid quantity
        )
        with self.assertRaises(ValidationError) as cm:
            temp_booking_addon.clean()
        self.assertIn('quantity', cm.exception.message_dict)
        self.assertEqual(
            cm.exception.message_dict['quantity'][0],
            f"Quantity for {self.addon_min2_max2.name} cannot be less than {self.addon_min2_max2.min_quantity}."
        )

    def test_clean_quantity_greater_than_max_quantity_raises_error(self):
        """
        Test that clean() raises ValidationError if quantity is greater than addon's max_quantity.
        """
        temp_booking_addon = create_temp_booking_addon(
            temp_booking=self.temp_booking,
            addon=self.addon_min2_max2, # max_quantity is 2
            quantity=3 # Invalid quantity
        )
        with self.assertRaises(ValidationError) as cm:
            temp_booking_addon.clean()
        self.assertIn('quantity', cm.exception.message_dict)
        self.assertEqual(
            cm.exception.message_dict['quantity'][0],
            f"Quantity for {self.addon_min2_max2.name} cannot be more than {self.addon_min2_max2.max_quantity}."
        )

    def test_clean_quantity_null_raises_error(self):
        """
        Test that clean() raises ValidationError if quantity is null when addon is selected.
        """
        temp_booking_addon = create_temp_booking_addon(
            temp_booking=self.temp_booking,
            addon=self.addon_min1_max5,
            quantity=1 # Create with valid quantity first
        )
        temp_booking_addon.quantity = None # Then set to null
        with self.assertRaises(ValidationError) as cm:
            temp_booking_addon.clean()
        self.assertIn('quantity', cm.exception.message_dict)
        self.assertEqual(cm.exception.message_dict['quantity'][0], "Quantity cannot be null.")

    def test_clean_booked_addon_price_mismatch_raises_error(self):
        """
        Test that clean() raises ValidationError if booked_addon_price does not match
        the current add-on cost.
        """
        temp_booking_addon = create_temp_booking_addon(
            temp_booking=self.temp_booking,
            addon=self.addon_min1_max5,
            quantity=1,
            booked_addon_price=Decimal('9.99') # Mismatch
        )
        with self.assertRaises(ValidationError) as cm:
            temp_booking_addon.clean()
        self.assertIn('booked_addon_price', cm.exception.message_dict)
        self.assertEqual(
            cm.exception.message_dict['booked_addon_price'][0],
            f"Booked add-on price must match the current price of the add-on ({self.addon_min1_max5.cost})."
        )

    def test_clean_valid_temp_booking_addon_passes(self):
        """
        Test that a valid TempBookingAddOn instance passes clean() without errors.
        """
        temp_booking_addon = create_temp_booking_addon(
            temp_booking=self.temp_booking,
            addon=self.addon_min1_max5,
            quantity=3, # Within min/max range
            booked_addon_price=self.addon_min1_max5.cost # Match
        )
        try:
            temp_booking_addon.clean()
        except ValidationError:
            self.fail("ValidationError raised unexpectedly for a valid TempBookingAddOn.")

    def test_clean_valid_temp_booking_addon_with_deleted_addon_passes(self):
        """
        Test that clean() passes for TempBookingAddOn if addon is null (deleted).
        In this case, quantity and booked_addon_price validation should be skipped.
        """
        # Create the instance directly to ensure addon is None
        temp_booking_addon = TempBookingAddOn.objects.create(
            temp_booking=self.temp_booking,
            addon=None, # Simulate deleted addon
            quantity=1,
            booked_addon_price=Decimal('10.00') # Price can be anything if addon is null
        )
        try:
            temp_booking_addon.clean()
        except ValidationError:
            self.fail("ValidationError raised unexpectedly for TempBookingAddOn with deleted addon.")

