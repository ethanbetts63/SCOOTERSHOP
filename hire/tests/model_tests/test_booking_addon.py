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
    create_hire_settings, # Import create_hire_settings
)

# Import the pricing utility (needed for accurate expected values)
from hire.views.hire_pricing import calculate_addon_price
import datetime
from django.utils import timezone


class BookingAddOnModelTest(TestCase):
    """
    Unit tests for the BookingAddOn model.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up non-modified objects used by all test methods.
        """
        # Ensure HireSettings exists for validation checks
        cls.hire_settings = create_hire_settings(
            hire_pricing_strategy='24_hour_customer_friendly', # Ensure strategy is set
            excess_hours_margin=2 # Ensure margin is set
        )

        cls.motorcycle = create_motorcycle()
        
        # Define specific dates and times for the booking to ensure consistent duration calculation
        cls.pickup_date = timezone.now().date() + datetime.timedelta(days=1)
        cls.pickup_time = datetime.time(10, 0)
        cls.return_date = cls.pickup_date + datetime.timedelta(days=2) # This makes it span 3 calendar days
        cls.return_time = datetime.time(16, 0) # 6 hours into the third day

        cls.driver_profile = create_driver_profile()
        cls.booking = create_hire_booking(
            motorcycle=cls.motorcycle,
            driver_profile=cls.driver_profile,
            pickup_date=cls.pickup_date,
            pickup_time=cls.pickup_time,
            return_date=cls.return_date,
            return_time=cls.return_time,
            grand_total=Decimal('100.00') # This value might need to be dynamic if calculated in future tests
        )
        # Addon with daily_cost 10.00, hourly_cost 2.00
        cls.available_addon = create_addon(name="Available AddOn", daily_cost=Decimal('10.00'), hourly_cost=Decimal('2.00'), is_available=True)
        cls.unavailable_addon = create_addon(name="Unavailable AddOn", daily_cost=Decimal('20.00'), hourly_cost=Decimal('4.00'), is_available=False)

        # Calculate the expected price per unit for the default booking duration
        # This will be used to correctly assert prices in tests
        cls.expected_addon_price_per_unit_for_default_booking = calculate_addon_price(
            addon_instance=cls.available_addon,
            quantity=1, # Calculate for a single unit
            pickup_date=cls.booking.pickup_date,
            return_date=cls.booking.return_date,
            pickup_time=cls.booking.pickup_time,
            return_time=cls.booking.return_time,
            hire_settings=cls.hire_settings
        )

    def test_create_basic_booking_addon(self):
        """
        Test that a basic BookingAddOn instance can be created.
        """
        # The factory sets booked_addon_price as addon.daily_cost * quantity by default
        # For a 2-day booking (default in create_hire_booking), daily cost is used.
        # So, 10.00 (daily_cost) * 2 (quantity) = 20.00. This was the old logic.
        # Now, the expected price is calculated based on duration and strategy.
        quantity = 2
        expected_booked_price = self.expected_addon_price_per_unit_for_default_booking * quantity
        booking_addon = create_booking_addon(
            booking=self.booking,
            addon=self.available_addon,
            quantity=quantity,
            booked_addon_price=expected_booked_price # Pass the expected total price
        )
        self.assertIsNotNone(booking_addon.pk)
        self.assertEqual(booking_addon.booking, self.booking)
        self.assertEqual(booking_addon.addon, self.available_addon)
        self.assertEqual(booking_addon.quantity, quantity)
        self.assertEqual(booking_addon.booked_addon_price, expected_booked_price)

    def test_str_method(self):
        """
        Test the __str__ method of BookingAddOn.
        """
        booking_addon = create_booking_addon(
            booking=self.booking,
            addon=self.available_addon,
            quantity=3,
            booked_addon_price=self.expected_addon_price_per_unit_for_default_booking * 3
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
            quantity=1,
            booked_addon_price=self.expected_addon_price_per_unit_for_default_booking * 1
        )
        with self.assertRaises(IntegrityError):
            create_booking_addon(
                booking=self.booking,
                addon=self.available_addon, # Same addon for same booking
                quantity=2, # Quantity doesn't matter for uniqueness
                booked_addon_price=self.expected_addon_price_per_unit_for_default_booking * 2
            )

    # --- clean() method tests ---

    def test_clean_unavailable_addon_raises_error(self):
        """
        Test that clean() raises ValidationError if the selected add-on is not available.
        """
        booking_addon = create_booking_addon(
            booking=self.booking,
            addon=self.unavailable_addon, # This addon is not available
            quantity=1,
            # Pass a dummy price, as the availability check should fail first
            booked_addon_price=Decimal('0.00') 
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
        the calculated total price.
        """
        # We pass a price that is intentionally incorrect to trigger the validation error.
        # The expected calculated price is self.expected_addon_price_per_unit_for_default_booking * quantity
        quantity = 1
        incorrect_booked_price = self.expected_addon_price_per_unit_for_default_booking * quantity + Decimal('0.01') # Mismatch
        
        booking_addon = create_booking_addon(
            booking=self.booking,
            addon=self.available_addon,
            quantity=quantity,
            booked_addon_price=incorrect_booked_price 
        )
        with self.assertRaises(ValidationError) as cm:
            booking_addon.clean()
        self.assertIn('booked_addon_price', cm.exception.message_dict)
        
        # The expected calculated total price for 1 unit of Available AddOn for the booking duration
        expected_calculated_total_price = self.expected_addon_price_per_unit_for_default_booking * quantity
        
        self.assertEqual(
            cm.exception.message_dict['booked_addon_price'][0],
            f"Booked add-on price ({incorrect_booked_price}) must match the calculated total price "
            f"({expected_calculated_total_price}) for {quantity} unit(s) of {self.available_addon.name}."
        )

    def test_clean_valid_booking_addon_passes(self):
        """
        Test that a valid BookingAddOn instance passes clean() without errors.
        """
        # We pass a price that is intentionally correct to ensure validation passes.
        quantity = 1
        correct_booked_price = self.expected_addon_price_per_unit_for_default_booking * quantity
        
        booking_addon = create_booking_addon(
            booking=self.booking,
            addon=self.available_addon,
            quantity=quantity,
            booked_addon_price=correct_booked_price # Match the expected total price
        )
        try:
            booking_addon.clean()
        except ValidationError:
            self.fail("ValidationError raised unexpectedly for a valid BookingAddOn.")

