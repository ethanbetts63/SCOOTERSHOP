# hire/tests/model_tests/test_temp_booking_addon.py

import datetime
import uuid
from decimal import Decimal
from django.test import TestCase
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.utils import timezone
from django.db import IntegrityError
import time # Import the time module

# Import models
from hire.models import TempHireBooking, TempBookingAddOn
from inventory.models import Motorcycle
from payments.models import Payment # Although not directly linked, useful for context
from dashboard.models import HireSettings

# Import model factories
from hire.tests.test_helpers.model_factories import (
    create_motorcycle,
    create_driver_profile,
    create_package,
    create_addon,
    create_hire_settings,
    create_temp_hire_booking,
    create_temp_booking_addon,
)

# Import the pricing utility (needed for accurate expected values)
from hire.hire_pricing import calculate_addon_price


class TempBookingAddOnModelTest(TestCase):
    """
    Unit tests for the TempBookingAddOn model.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up non-modified objects used by all test methods.
        This runs once for the entire test class.
        """
        cls.motorcycle = create_motorcycle()
        cls.driver_profile = create_driver_profile()
        cls.package = create_package()
        cls.addon1 = create_addon(name="AddOn A", hourly_cost=Decimal('2.00'), daily_cost=Decimal('15.00'))
        cls.addon2 = create_addon(name="AddOn B", hourly_cost=Decimal('5.00'), daily_cost=Decimal('20.00'))
        cls.hire_settings = create_hire_settings(
            hire_pricing_strategy='24_hour_customer_friendly', # Ensure strategy is set
            excess_hours_margin=2 # Ensure margin is set
        )

        # Define specific dates and times for the temporary booking to ensure consistent duration calculation
        cls.pickup_date = timezone.now().date() + datetime.timedelta(days=1)
        cls.pickup_time = datetime.time(10, 0)
        cls.return_date = cls.pickup_date + datetime.timedelta(days=2) # This makes it span 3 calendar days
        cls.return_time = datetime.time(16, 0) # 6 hours into the third day

        # This temp_booking is created once for the class and will exist for all tests.
        # Tests that need an isolated count should create their own temp_booking and manage its lifecycle.
        cls.temp_booking_for_addons = create_temp_hire_booking(
            motorcycle=cls.motorcycle,
            pickup_date=cls.pickup_date,
            pickup_time=cls.pickup_time,
            return_date=cls.return_date,
            return_time=cls.return_time,
            grand_total=Decimal('100.00') # This value might need to be dynamic if calculated in future tests
        )

        # Calculate the expected price per unit for addon1 for the default temp booking duration
        cls.expected_addon1_price_per_unit_for_default_temp_booking = calculate_addon_price(
            addon_instance=cls.addon1,
            quantity=1, # Calculate for a single unit
            pickup_date=cls.temp_booking_for_addons.pickup_date,
            return_date=cls.temp_booking_for_addons.return_date,
            pickup_time=cls.temp_booking_for_addons.pickup_time,
            return_time=cls.temp_booking_for_addons.return_time,
            hire_settings=cls.hire_settings
        )
        # Calculate the expected price per unit for addon2 for the default temp booking duration
        cls.expected_addon2_price_per_unit_for_default_temp_booking = calculate_addon_price(
            addon_instance=cls.addon2,
            quantity=1, # Calculate for a single unit
            pickup_date=cls.temp_booking_for_addons.pickup_date,
            return_date=cls.temp_booking_for_addons.return_date,
            pickup_time=cls.temp_booking_for_addons.pickup_time,
            return_time=cls.temp_booking_for_addons.return_time,
            hire_settings=cls.hire_settings
        )


    def test_create_basic_temp_hire_booking(self):
        """
        Test that a basic TempHireBooking instance can be created.
        """
        # Get initial count to ensure this test is isolated in its assertion
        initial_temp_booking_count = TempHireBooking.objects.count()

        temp_booking = create_temp_hire_booking(
            motorcycle=self.motorcycle,
            driver_profile=self.driver_profile,
            grand_total=Decimal('150.00')
        )
        self.assertIsNotNone(temp_booking.pk)
        self.assertEqual(temp_booking.motorcycle, self.motorcycle)
        self.assertEqual(temp_booking.driver_profile, self.driver_profile)
        self.assertEqual(temp_booking.grand_total, Decimal('150.00'))
        self.assertIsNotNone(temp_booking.session_uuid)
        self.assertFalse(temp_booking.has_motorcycle_license) # Default value
        self.assertEqual(TempHireBooking.objects.count(), initial_temp_booking_count + 1)


    def test_session_uuid_uniqueness(self):
        """
        Test that session_uuid is unique.
        """
        # Create one temp booking with a specific UUID
        create_temp_hire_booking(
            session_uuid=uuid.UUID('12345678-1234-5678-1234-567812345678'),
            motorcycle=self.motorcycle,
            driver_profile=self.driver_profile,
            grand_total=Decimal('100.00')
        )

        # Attempt to create another with the same UUID
        with self.assertRaises(IntegrityError):
            create_temp_hire_booking(
                session_uuid=uuid.UUID('12345678-1234-5678-1234-567812345678'),
                motorcycle=self.motorcycle,
                driver_profile=self.driver_profile,
                grand_total=Decimal('200.00')
            )

    def test_str_method(self):
        """
        Test the __str__ method of TempHireBooking.
        """
        temp_booking = create_temp_hire_booking(
            motorcycle=self.motorcycle,
            pickup_date=datetime.date(2025, 7, 1),
            return_date=datetime.date(2025, 7, 3),
            session_uuid=uuid.UUID('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa')
        )
        expected_str = f"Temp Booking (aaaaaaaa): {self.motorcycle.model} (2025-07-01 to 2025-07-03)"
        self.assertEqual(str(temp_booking), expected_str)

        # Test with no motorcycle
        temp_booking_no_bike = create_temp_hire_booking(
            motorcycle=None,
            pickup_date=datetime.date(2025, 8, 1),
            return_date=datetime.date(2025, 8, 3),
            session_uuid=uuid.UUID('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb')
        )
        expected_str_no_bike = "Temp Booking (bbbbbbbb): No bike selected (2025-08-01 to 2025-08-03)"
        self.assertEqual(str(temp_booking_no_bike), expected_str_no_bike)

    def test_relationships(self):
        """
        Test that foreign key relationships are correctly established.
        """
        temp_booking = create_temp_hire_booking(
            motorcycle=self.motorcycle,
            driver_profile=self.driver_profile,
            package=self.package
        )
        self.assertEqual(temp_booking.motorcycle, self.motorcycle)
        self.assertEqual(temp_booking.driver_profile, self.driver_profile)
        self.assertEqual(temp_booking.package, self.package)

    def test_default_values(self):
        """
        Test that default values are correctly applied when not provided.
        """
        temp_booking = create_temp_hire_booking(
            motorcycle=self.motorcycle,
            driver_profile=self.driver_profile,
            grand_total=Decimal('100.00')
        )
        self.assertFalse(temp_booking.has_motorcycle_license)
        self.assertEqual(temp_booking.total_addons_price, Decimal('0.00'))
        self.assertEqual(temp_booking.total_package_price, Decimal('0.00'))
        self.assertEqual(temp_booking.currency, 'AUD')
        self.assertEqual(temp_booking.payment_option, 'online_full') # Default from factory

    def test_nullable_fields(self):
        """
        Test that nullable fields can be created as None/blank.
        """
        temp_booking = TempHireBooking.objects.create(
            session_uuid=uuid.uuid4(),
            has_motorcycle_license=True, # Minimal required fields
            currency='USD' # Override default
        )
        self.assertIsNone(temp_booking.pickup_date)
        self.assertIsNone(temp_booking.motorcycle)
        self.assertIsNone(temp_booking.grand_total)
        self.assertEqual(temp_booking.currency, 'USD')

    def test_temp_booking_addon_creation(self):
        """
        Test that TempBookingAddOn instances can be created and linked.
        """
        temp_booking = create_temp_hire_booking(
            motorcycle=self.motorcycle,
            driver_profile=self.driver_profile,
            grand_total=Decimal('200.00'),
            pickup_date=self.pickup_date,
            pickup_time=self.pickup_time,
            return_date=self.return_date,
            return_time=self.return_time,
        )
        
        # For addon1 (daily_cost 15.00) and quantity 2
        quantity1 = 2
        expected_price1 = self.expected_addon1_price_per_unit_for_default_temp_booking * quantity1
        temp_addon1 = create_temp_booking_addon(
            temp_booking,
            self.addon1,
            quantity=quantity1,
            booked_addon_price=expected_price1
        )
        
        # For addon2 (daily_cost 20.00) and quantity 1. We pass 22.00 to test custom value.
        quantity2 = 1
        custom_booked_price2 = Decimal('22.00') # Intentionally different from calculated
        temp_addon2 = create_temp_booking_addon(
            temp_booking,
            self.addon2,
            quantity=quantity2,
            booked_addon_price=custom_booked_price2
        )

        self.assertIsNotNone(temp_addon1.pk)
        self.assertEqual(temp_addon1.temp_booking, temp_booking)
        self.assertEqual(temp_addon1.addon, self.addon1)
        self.assertEqual(temp_addon1.quantity, quantity1)
        self.assertEqual(temp_addon1.booked_addon_price, expected_price1) # Expected total price

        self.assertIsNotNone(temp_addon2.pk)
        self.assertEqual(temp_addon2.temp_booking, temp_booking)
        self.assertEqual(temp_addon2.addon, self.addon2)
        self.assertEqual(temp_addon2.quantity, quantity2)
        self.assertEqual(temp_addon2.booked_addon_price, custom_booked_price2)

        # Check reverse relationship
        linked_addons = temp_booking.temp_booking_addons.all()
        self.assertEqual(linked_addons.count(), 2)
        self.assertIn(temp_addon1, linked_addons)
        self.assertIn(temp_addon2, linked_addons)

    def test_delete_temp_booking_deletes_addons(self):
        """
        Test that deleting a TempHireBooking also deletes its associated TempBookingAddOn instances.
        """
        # Get the initial count of TempHireBooking objects before creating a new one for this test
        initial_temp_booking_count = TempHireBooking.objects.count()
        initial_temp_addon_count = TempBookingAddOn.objects.count()

        # Create a new temp booking specifically for this deletion test
        temp_booking_to_delete = create_temp_hire_booking(
            motorcycle=self.motorcycle,
            driver_profile=self.driver_profile,
            grand_total=Decimal('200.00'),
            pickup_date=self.pickup_date,
            pickup_time=self.pickup_time,
            return_date=self.return_date,
            return_time=self.return_time,
        )
        # Create associated add-ons for this specific temp booking
        create_temp_booking_addon(temp_booking_to_delete, self.addon1, quantity=1, booked_addon_price=self.expected_addon1_price_per_unit_for_default_temp_booking * 1)
        create_temp_booking_addon(temp_booking_to_delete, self.addon2, quantity=1, booked_addon_price=self.expected_addon2_price_per_unit_for_default_temp_booking * 1)

        # Assert that the count of temp bookings increased by 1 and add-ons by 2
        self.assertEqual(TempHireBooking.objects.count(), initial_temp_booking_count + 1)
        self.assertEqual(TempBookingAddOn.objects.count(), initial_temp_addon_count + 2)

        # Now delete the specific temp booking
        temp_booking_to_delete.delete()

        # Assert that the counts have returned to their initial state (or decreased by the deleted objects)
        self.assertEqual(TempHireBooking.objects.count(), initial_temp_booking_count)
        self.assertEqual(TempBookingAddOn.objects.count(), initial_temp_addon_count)


    def test_update_temp_hire_booking(self):
        """
        Test that a TempHireBooking instance can be updated.
        """
        temp_booking = create_temp_hire_booking(
            motorcycle=self.motorcycle,
            driver_profile=self.driver_profile,
            grand_total=Decimal('100.00'),
            has_motorcycle_license=False,
            pickup_date=self.pickup_date,
            pickup_time=self.pickup_time,
            return_date=self.return_date,
            return_time=self.return_time,
        )

        # Introduce a small delay to ensure updated_at is greater than created_at
        time.sleep(0.001)

        new_total = Decimal('250.00')
        temp_booking.grand_total = new_total
        temp_booking.has_motorcycle_license = True
        temp_booking.save()

        updated_booking = TempHireBooking.objects.get(pk=temp_booking.pk)
        self.assertEqual(updated_booking.grand_total, new_total)
        self.assertTrue(updated_booking.has_motorcycle_license)
        self.assertGreater(updated_booking.updated_at, updated_booking.created_at)

    def test_clean_booked_addon_price_mismatch_raises_error(self):
        """
        Test that clean() raises ValidationError if booked_addon_price does not match
        the calculated total price.
        """
        # Create a fresh temp booking with defined dates/times for accurate price calculation
        temp_booking = create_temp_hire_booking(
            motorcycle=self.motorcycle,
            pickup_date=self.pickup_date,
            pickup_time=self.pickup_time,
            return_date=self.return_date,
            return_time=self.return_time,
        )
        
        quantity = 2
        # We pass a price that is intentionally incorrect to trigger the validation error.
        incorrect_booked_price = self.expected_addon1_price_per_unit_for_default_temp_booking * quantity + Decimal('0.01') # Mismatch
        
        temp_booking_addon = create_temp_booking_addon(
            temp_booking=temp_booking,
            addon=self.addon1,
            quantity=quantity,
            booked_addon_price=incorrect_booked_price 
        )
        with self.assertRaises(ValidationError) as cm:
            temp_booking_addon.clean()
        self.assertIn('booked_addon_price', cm.exception.message_dict)
        
        # The expected calculated total price for 2 units of AddOn A for the booking duration
        expected_calculated_total_price = self.expected_addon1_price_per_unit_for_default_temp_booking * quantity
        
        self.assertEqual(
            cm.exception.message_dict['booked_addon_price'][0],
            f"Booked add-on price ({incorrect_booked_price}) must match the calculated total price "
            f"({expected_calculated_total_price}) for {quantity} unit(s) of {self.addon1.name}."
        )

    def test_clean_valid_temp_booking_addon_passes(self):
        """
        Test that a valid TempBookingAddOn instance passes clean() without errors.
        """
        # Create a fresh temp booking with defined dates/times for accurate price calculation
        temp_booking = create_temp_hire_booking(
            motorcycle=self.motorcycle,
            pickup_date=self.pickup_date,
            pickup_time=self.pickup_time,
            return_date=self.return_date,
            return_time=self.return_time,
        )
        
        quantity = 2
        # We pass a price that is intentionally correct to ensure validation passes.
        correct_booked_price = self.expected_addon1_price_per_unit_for_default_temp_booking * quantity
        
        temp_booking_addon = create_temp_booking_addon(
            temp_booking=temp_booking,
            addon=self.addon1,
            quantity=quantity,
            booked_addon_price=correct_booked_price # Match the expected total price
        )
        try:
            temp_booking_addon.clean()
        except ValidationError:
            self.fail("ValidationError raised unexpectedly for a valid TempBookingAddOn.")

