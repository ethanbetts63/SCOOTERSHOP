# hire/tests/model_tests/test_temp_hire_booking.py

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


class TempHireBookingModelTest(TestCase):
    """
    Unit tests for the TempHireBooking model.
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
        cls.addon1 = create_addon(name="GPS", hourly_cost=Decimal('2.00'), daily_cost=Decimal('15.00'))
        cls.addon2 = create_addon(name="Extra Helmet", hourly_cost=Decimal('5.00'), daily_cost=Decimal('20.00'))
        cls.hire_settings = create_hire_settings() # Ensure settings exist

    def test_create_basic_temp_hire_booking(self):
        """
        Test that a basic TempHireBooking instance can be created.
        """
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

    def test_session_uuid_uniqueness(self):
        """
        Test that session_uuid is unique.
        """
        # Create one temp booking
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
            grand_total=Decimal('200.00')
        )
        temp_addon1 = create_temp_booking_addon(temp_booking, self.addon1, quantity=2)
        temp_addon2 = create_temp_booking_addon(temp_booking, self.addon2, quantity=1, booked_addon_price=Decimal('22.00'))

        self.assertIsNotNone(temp_addon1.pk)
        self.assertEqual(temp_addon1.temp_booking, temp_booking)
        self.assertEqual(temp_addon1.addon, self.addon1)
        self.assertEqual(temp_addon1.quantity, 2)
        # The default for booked_addon_price in factory is addon.daily_cost * quantity
        self.assertEqual(temp_addon1.booked_addon_price, self.addon1.daily_cost * 2)

        self.assertIsNotNone(temp_addon2.pk)
        self.assertEqual(temp_addon2.temp_booking, temp_booking)
        self.assertEqual(temp_addon2.addon, self.addon2)
        self.assertEqual(temp_addon2.quantity, 1)
        self.assertEqual(temp_addon2.booked_addon_price, Decimal('22.00'))

        # Check reverse relationship
        linked_addons = temp_booking.temp_booking_addons.all()
        self.assertEqual(linked_addons.count(), 2)
        self.assertIn(temp_addon1, linked_addons)
        self.assertIn(temp_addon2, linked_addons)

    def test_delete_temp_booking_deletes_addons(self):
        """
        Test that deleting a TempHireBooking also deletes its associated TempBookingAddOn instances.
        """
        temp_booking = create_temp_hire_booking(
            motorcycle=self.motorcycle,
            driver_profile=self.driver_profile,
            grand_total=Decimal('200.00')
        )
        create_temp_booking_addon(temp_booking, self.addon1, quantity=1)
        create_temp_booking_addon(temp_booking, self.addon2, quantity=1)

        self.assertEqual(TempHireBooking.objects.count(), 1)
        self.assertEqual(TempBookingAddOn.objects.count(), 2)

        temp_booking.delete()

        self.assertEqual(TempHireBooking.objects.count(), 0)
        self.assertEqual(TempBookingAddOn.objects.count(), 0)

    def test_update_temp_hire_booking(self):
        """
        Test that a TempHireBooking instance can be updated.
        """
        temp_booking = create_temp_hire_booking(
            motorcycle=self.motorcycle,
            driver_profile=self.driver_profile,
            grand_total=Decimal('100.00'),
            has_motorcycle_license=False
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

