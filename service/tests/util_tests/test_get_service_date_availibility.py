from django.test import TestCase
import datetime
import json
from unittest.mock import patch

# Import the function to be tested
from service.utils.get_service_date_availibility import get_service_date_availability

# Import models and factories
from service.models import ServiceSettings, BlockedServiceDate, ServiceBooking
from ..test_helpers.model_factories import (
    ServiceSettingsFactory,
    BlockedServiceDateFactory,
    ServiceBookingFactory,
    ServiceProfileFactory,
    ServiceTypeFactory,
    CustomerMotorcycleFactory,
)

from faker import Faker
fake = Faker()

class GetServiceDateAvailabilityTest(TestCase):
    """
    Tests for the get_service_date_availability utility function.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up common data for all tests in this class.
        We'll use a mocked timezone to ensure consistent test results regardless of execution time.
        """
        # Patch timezone.now() and timezone.localtime() to return a fixed date/time
        # This is crucial for date-dependent tests.
        cls.fixed_now = datetime.datetime(2025, 6, 15, 10, 0, 0, tzinfo=datetime.timezone.utc)
        cls.fixed_local_date = datetime.date(2025, 6, 15) # Corresponds to a Sunday

        # Mock timezone.now and timezone.localtime
        cls.patcher_now = patch('django.utils.timezone.now', return_value=cls.fixed_now)
        cls.patcher_localtime = patch('django.utils.timezone.localtime', return_value=cls.fixed_now)

        cls.mock_now = cls.patcher_now.start()
        cls.mock_localtime = cls.patcher_localtime.start()

        # Ensure ServiceSettings exists for all tests
        # We'll create it once here and then modify it as needed in individual tests
        cls.service_settings = ServiceSettingsFactory(
            booking_advance_notice=1, # Default advance notice
            max_visible_slots_per_day=3, # Default max slots
            booking_open_days="Mon,Tue,Wed,Thu,Fri,Sat,Sun" # All days open by default
        )

        # Create base related objects for ServiceBookingFactory
        # These are common instances that can be used if *not* creating multiple related objects
        cls.service_profile = ServiceProfileFactory()
        cls.service_type = ServiceTypeFactory()
        cls.customer_motorcycle = CustomerMotorcycleFactory(service_profile=cls.service_profile)
        # Removed cls.payment as it was causing the unique constraint error when reused.
        # ServiceBookingFactory will now create a new Payment for each booking by default.

    @classmethod
    def tearDownClass(cls):
        """
        Clean up mocks after all tests are done.
        """
        cls.patcher_now.stop()
        cls.patcher_localtime.stop()
        super().tearDownClass()

    def setUp(self):
        """
        Set up for each test method. Clear out any previous data.
        """
        # Clear existing ServiceSettings and create a fresh one for each test if necessary,
        # or reset its values. For now, we'll just reset it.
        self.service_settings.booking_advance_notice = 1
        self.service_settings.max_visible_slots_per_day = 3
        self.service_settings.booking_open_days = "Mon,Tue,Wed,Thu,Fri,Sat,Sun"
        self.service_settings.save()

        BlockedServiceDate.objects.all().delete()
        ServiceBooking.objects.all().delete()

    def test_min_date_with_advance_notice(self):
        """
        Test that min_date is correctly calculated based on booking_advance_notice.
        """
        # Test 1 day advance notice (default)
        # fixed_local_date is June 15, 2025 (Sunday)
        self.service_settings.booking_advance_notice = 1
        self.service_settings.save()
        min_date, _ = get_service_date_availability()
        expected_min_date = self.fixed_local_date + datetime.timedelta(days=1) # June 16, 2025 (Monday)
        self.assertEqual(min_date, expected_min_date)

        # Test 0 days advance notice (today is available)
        self.service_settings.booking_advance_notice = 0
        self.service_settings.save()
        min_date, _ = get_service_date_availability()
        expected_min_date = self.fixed_local_date # June 15, 2025 (Sunday)
        self.assertEqual(min_date, expected_min_date)

        # Test 7 days advance notice
        self.service_settings.booking_advance_notice = 7
        self.service_settings.save()
        min_date, _ = get_service_date_availability()
        expected_min_date = self.fixed_local_date + datetime.timedelta(days=7) # June 22, 2025 (Sunday)
        self.assertEqual(min_date, expected_min_date)

    def test_blocked_service_dates(self):
        """
        Test that explicitly blocked dates are disabled.
        """
        # Block a single day
        BlockedServiceDateFactory(
            start_date=datetime.date(2025, 6, 20), # A Friday
            end_date=datetime.date(2025, 6, 20)
        )
        # Block a range of days
        BlockedServiceDateFactory(
            start_date=datetime.date(2025, 6, 25), # A Wednesday
            end_date=datetime.date(2025, 6, 27)  # A Friday
        )

        min_date, disabled_dates_json = get_service_date_availability()
        disabled_dates = json.loads(disabled_dates_json)

        # Check single blocked day
        self.assertIn({'from': '2025-06-20', 'to': '2025-06-20'}, disabled_dates)
        # Check blocked range
        self.assertIn({'from': '2025-06-25', 'to': '2025-06-27'}, disabled_dates)

    def test_non_booking_open_days(self):
        """
        Test that days not specified in booking_open_days are disabled.
        Fixed current date is Sunday, June 15, 2025.
        """
        # Only allow Monday and Tuesday bookings
        self.service_settings.booking_open_days = "Mon,Tue"
        self.service_settings.booking_advance_notice = 0 # Allow today to be checked
        self.service_settings.save()

        min_date, disabled_dates_json = get_service_date_availability()
        disabled_dates = json.loads(disabled_dates_json)

        # Dates to expect as disabled based on fixed_local_date (June 15, 2025 - Sunday)
        # June 15 (Sunday) should be disabled
        self.assertIn('2025-06-15', disabled_dates)
        # June 16 (Monday) should NOT be disabled as 'Mon' is in open_days_list
        self.assertNotIn('2025-06-16', disabled_dates)
        # June 17 (Tuesday) should NOT be disabled as 'Tue' is in open_days_list
        self.assertNotIn('2025-06-17', disabled_dates)
        # June 18 (Wednesday) should be disabled
        self.assertIn('2025-06-18', disabled_dates)
        # June 19 (Thursday) should be disabled
        self.assertIn('2025-06-19', disabled_dates)
        # June 20 (Friday) should be disabled
        self.assertIn('2025-06-20', disabled_dates)
        # June 21 (Saturday) should be disabled
        self.assertIn('2025-06-21', disabled_dates)
        # June 22 (Sunday) should be disabled
        self.assertIn('2025-06-22', disabled_dates)

    def test_max_visible_slots_capacity(self):
        """
        Test that days reaching max_visible_slots_per_day are disabled.
        """
        self.service_settings.max_visible_slots_per_day = 1 # Only 1 slot per day
        self.service_settings.booking_advance_notice = 0 # Check from today
        self.service_settings.save()

        today = self.fixed_local_date # June 15, 2025 (Sunday)
        tomorrow = today + datetime.timedelta(days=1) # June 16, 2025 (Monday)

        # Create one booking for today. Payment field will be automatically generated.
        ServiceBookingFactory(
            service_profile=self.service_profile,
            service_type=self.service_type,
            customer_motorcycle=self.customer_motorcycle,
            dropoff_date=today,
            service_date=today,
            dropoff_time=datetime.time(9,0,0),
            booking_status='confirmed' # FIX: Changed from 'booked' to 'confirmed'
        )

        min_date, disabled_dates_json = get_service_date_availability()
        disabled_dates = json.loads(disabled_dates_json)

        # Today should be disabled because max_slots is 1 and there is 1 booking.
        self.assertIn(str(today), disabled_dates)
        self.assertNotIn(str(tomorrow), disabled_dates) # Tomorrow should still be open

        # Create another booking for tomorrow to disable it too
        ServiceBookingFactory(
            service_profile=self.service_profile,
            service_type=self.service_type,
            customer_motorcycle=self.customer_motorcycle,
            dropoff_date=tomorrow,
            service_date=tomorrow,
            dropoff_time=datetime.time(9,30,0),
            booking_status='in_progress'
        )

        min_date, disabled_dates_json = get_service_date_availability()
        disabled_dates = json.loads(disabled_dates_json)

        self.assertIn(str(today), disabled_dates)
        self.assertIn(str(tomorrow), disabled_dates)


    def test_combined_rules(self):
        """
        Test a scenario where multiple rules apply to disable a date.
        """
        self.service_settings.booking_advance_notice = 0
        self.service_settings.max_visible_slots_per_day = 1
        self.service_settings.booking_open_days = "Mon" # Only Monday is open
        self.service_settings.save()

        # Fixed date is Sunday, June 15, 2025
        # June 15 (Sunday) should be disabled by booking_open_days (Sunday is not Mon)
        # June 16 (Monday) is an open day, so it should NOT be disabled by booking_open_days.

        # Block Monday, June 17
        BlockedServiceDateFactory(
            start_date=datetime.date(2025, 6, 17),
            end_date=datetime.date(2025, 6, 17)
        )

        min_date, disabled_dates_json = get_service_date_availability()
        disabled_dates = json.loads(disabled_dates_json)

        # June 15 (Sunday) should be disabled by open days
        self.assertIn('2025-06-15', disabled_dates)
        # June 16 (Monday) should NOT be disabled by open days (it's a Monday)
        self.assertNotIn('2025-06-16', disabled_dates)
        # June 17 (Tuesday) should be disabled because it's explicitly blocked AND not an open day ('Tue' is not 'Mon')
        # Ensure that both dictionary format (from BlockedServiceDate) and string format (from other rules) are handled.
        self.assertIn({'from': '2025-06-17', 'to': '2025-06-17'}, disabled_dates)
        # The other rules (open days, capacity) add dates as strings.
        # If a date is blocked by multiple rules, it might appear as a string or a dict.
        # For simplicity, we can check for the string representation if it's expected to be a single date.
        self.assertIn('2025-06-17', disabled_dates) # Also check as string for non-range block


        # Check if a date beyond the blocked period is still available (e.g., next Monday)
        # Next Monday would be June 23, 2025 (Monday) which should be open.
        self.assertNotIn('2025-06-23', disabled_dates) # Should be available if not blocked by other means

    def test_no_service_settings(self):
        """
        Test behavior when no ServiceSettings instance exists.
        Should default to current date for min_date and no disabled dates beyond blocked.
        """
        ServiceSettings.objects.all().delete() # Remove the default settings

        # Block a date to ensure only blocked dates are disabled
        BlockedServiceDateFactory(
            start_date=self.fixed_local_date + datetime.timedelta(days=5),
            end_date=self.fixed_local_date + datetime.timedelta(days=5)
        )

        min_date, disabled_dates_json = get_service_date_availability()
        disabled_dates = json.loads(disabled_dates_json)

        # min_date should be the current local date
        self.assertEqual(min_date, self.fixed_local_date)

        # Only the explicitly blocked date should be in disabled_dates
        expected_blocked = {'from': str(self.fixed_local_date + datetime.timedelta(days=5)),
                            'to': str(self.fixed_local_date + datetime.timedelta(days=5))}
        self.assertEqual(len(disabled_dates), 1)
        self.assertIn(expected_blocked, disabled_dates)

    def test_empty_booking_open_days(self):
        """
        Test when booking_open_days is an empty string or None.
        Should effectively disable all days if no valid open days are provided.
        """
        # Set to an invalid string that won't match any weekday abbreviations
        self.service_settings.booking_open_days = "INVALID"
        self.service_settings.booking_advance_notice = 0
        self.service_settings.save()

        min_date, disabled_dates_json = get_service_date_availability()
        disabled_dates = json.loads(disabled_dates_json)

        # Expect all days from today onwards (for the next 366 days) to be disabled
        for i in range(366):
            expected_date = self.fixed_local_date + datetime.timedelta(days=i)
            self.assertIn(str(expected_date), disabled_dates)

        # Test with a string that might lead to an empty list after split/strip if it were empty
        # However, as per model validation, it can't be truly empty.
        # This test ensures that if no valid open days are configured, all days are disabled.
        self.service_settings.booking_open_days = " " # Just spaces, leading to empty strings after strip
        self.service_settings.save()

        min_date, disabled_dates_json = get_service_date_availability()
        disabled_dates = json.loads(disabled_dates_json)
        for i in range(366):
            expected_date = self.fixed_local_date + datetime.timedelta(days=i)
            self.assertIn(str(expected_date), disabled_dates)


    def test_no_max_visible_slots_per_day_set(self):
        """
        Test when max_visible_slots_per_day is effectively unlimited (very high number).
        Capacity check should not disable any days.
        """
        self.service_settings.max_visible_slots_per_day = 99999 # Set to a very high number
        self.service_settings.booking_advance_notice = 0
        self.service_settings.save()

        today = self.fixed_local_date # June 15, 2025

        # Create many bookings for today, but it should not be disabled by capacity
        for _ in range(10):
            ServiceBookingFactory(
                service_profile=self.service_profile,
                service_type=self.service_type,
                customer_motorcycle=self.customer_motorcycle,
                dropoff_date=today,
                service_date=today,
                dropoff_time=datetime.time(9,0,0),
                booking_status='confirmed' # FIX: Changed from 'booked' to 'confirmed'
            )

        min_date, disabled_dates_json = get_service_date_availability()
        disabled_dates = json.loads(disabled_dates_json)

        # Today should not be in disabled_dates due to capacity (it's effectively unlimited)
        self.assertNotIn(str(today), disabled_dates)
        # Only check for the absence of the specific date, other rules might apply in real scenarios.

    def test_booking_status_filter(self):
        """
        Test that 'pending', 'confirmed', and 'in_progress' statuses count towards capacity.
        """
        self.service_settings.max_visible_slots_per_day = 1
        self.service_settings.booking_advance_notice = 0
        self.service_settings.save()

        today = self.fixed_local_date

        # This booking should count
        ServiceBookingFactory(
            service_profile=self.service_profile,
            service_type=self.service_type,
            customer_motorcycle=self.customer_motorcycle,
            dropoff_date=today,
            service_date=today,
            dropoff_time=datetime.time(10,0,0),
            booking_status='pending' # FIX: Changed status to one that now counts
        )
        # This booking should NOT count (as it's not in the ['pending', 'confirmed', 'in_progress'] list)
        ServiceBookingFactory(
            service_profile=self.service_profile,
            service_type=self.service_type,
            customer_motorcycle=self.customer_motorcycle,
            dropoff_date=today,
            service_date=today,
            dropoff_time=datetime.time(11,0,0),
            booking_status='cancelled' # This status should not contribute to capacity count
        )
        # This booking should NOT count (as it's not in the ['pending', 'confirmed', 'in_progress'] list)
        ServiceBookingFactory(
            service_profile=self.service_profile,
            service_type=self.service_type,
            customer_motorcycle=self.customer_motorcycle,
            dropoff_date=today,
            service_date=today,
            dropoff_time=datetime.time(12,0,0),
            booking_status='DECLINED_REFUNDED' # This status should not contribute to capacity count
        )

        min_date, disabled_dates_json = get_service_date_availability()
        disabled_dates = json.loads(disabled_dates_json)

        # Since only one booking counted towards capacity and max_slots is 1,
        # today should be disabled.
        self.assertIn(str(today), disabled_dates)

