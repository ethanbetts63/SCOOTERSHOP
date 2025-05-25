# hire/tests/model_tests/test_booking_addon.py

from decimal import Decimal
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db import IntegrityError

# Import model factories
from hire.tests.test_helpers.model_factories import (
    create_hire_booking,
    create_addon,
    create_booking_addon,
    create_motorcycle,
    create_driver_profile,
)


class BookingAddOnModelTest(TestCase):
    """
    Unit tests for the BookingAddOn model.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up non-modified objects used by all test methods.
        """
        cls.motorcycle = create_motorcycle()
        cls.driver_profile = create_driver_profile()
        cls.booking = create_hire_booking(
            motorcycle=cls.motorcycle,
            driver_profile=cls.driver_profile,
            total_price=Decimal('100.00')
        )
        cls.available_addon = create_addon(name="Available AddOn", cost=Decimal('10.00'), is_available=True)
        cls.unavailable_addon = create_addon(name="Unavailable AddOn", cost=Decimal('20.00'), is_available=False)

    def test_create_basic_booking_addon(self):
        """
        Test that a basic BookingAddOn instance can be created.
        """
        booking_addon = create_booking_addon(
            booking=self.booking,
            addon=self.available_addon,
            quantity=2,
            booked_addon_price=Decimal('10.00')
        )
        self.assertIsNotNone(booking_addon.pk)
        self.assertEqual(booking_addon.booking, self.booking)
        self.assertEqual(booking_addon.addon, self.available_addon)
        self.assertEqual(booking_addon.quantity, 2)
        self.assertEqual(booking_addon.booked_addon_price, Decimal('10.00'))

    def test_str_method(self):
        """
        Test the __str__ method of BookingAddOn.
        """
        booking_addon = create_booking_addon(
            booking=self.booking,
            addon=self.available_addon,
            quantity=3
        )
        expected_str = f"3 x {self.available_addon.name} for Booking {self.booking.booking_reference}"
        self.assertEqual(str(booking_addon), expected_str)

    def test_unique_together_constraint(self):
        """
        Test that unique_together constraint (booking, addon) prevents duplicates.
        """
        create_booking_addon(
            booking=self.booking,
            addon=self.available_addon,
            quantity=1
        )
        with self.assertRaises(IntegrityError):
            create_booking_addon(
                booking=self.booking,
                addon=self.available_addon, # Same addon for same booking
                quantity=2 # Quantity doesn't matter for uniqueness
            )

    # --- clean() method tests ---

    def test_clean_unavailable_addon_raises_error(self):
        """
        Test that clean() raises ValidationError if the selected add-on is not available.
        """
        booking_addon = create_booking_addon(
            booking=self.booking,
            addon=self.unavailable_addon, # This addon is not available
            quantity=1
        )
        with self.assertRaises(ValidationError) as cm:
            booking_addon.clean()
        self.assertIn('addon', cm.exception.message_dict)
        self.assertEqual(
            cm.exception.message_dict['addon'][0],
            f"The add-on '{self.unavailable_addon.name}' is currently not available."
        )

    def test_clean_booked_addon_price_mismatch_raises_error(self):
        """
        Test that clean() raises ValidationError if booked_addon_price does not match
        the current add-on cost.
        """
        booking_addon = create_booking_addon(
            booking=self.booking,
            addon=self.available_addon,
            quantity=1,
            booked_addon_price=Decimal('9.99') # Mismatch
        )
        with self.assertRaises(ValidationError) as cm:
            booking_addon.clean()
        self.assertIn('booked_addon_price', cm.exception.message_dict)
        self.assertEqual(
            cm.exception.message_dict['booked_addon_price'][0],
            f"Booked add-on price must match the current price of the add-on ({self.available_addon.cost})."
        )

    def test_clean_valid_booking_addon_passes(self):
        """
        Test that a valid BookingAddOn instance passes clean() without errors.
        """
        booking_addon = create_booking_addon(
            booking=self.booking,
            addon=self.available_addon,
            quantity=1,
            booked_addon_price=self.available_addon.cost # Match
        )
        try:
            booking_addon.clean()
        except ValidationError:
            self.fail("ValidationError raised unexpectedly for a valid BookingAddOn.")

