from django.test import TestCase
from django.utils import timezone
import datetime
from unittest.mock import patch
from service.models import ServiceSettings, ServiceBooking
# Corrected import path based on your feedback
from service.utils.get_available_service_dropoff_times import get_available_dropoff_times

# Corrected import path based on your feedback
from ..test_helpers.model_factories import (
    ServiceSettingsFactory,
    ServiceBookingFactory,
    ServiceProfileFactory,
    ServiceTypeFactory,
    CustomerMotorcycleFactory,
)

class GetAvailableDropoffTimesTest(TestCase):
    """
    Tests for the get_available_dropoff_times utility function.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up common data for all tests in this class.
        We'll use a mocked timezone to ensure consistent test results regardless of execution time.
        """
        # Patch timezone.now() to return a fixed date/time for consistent testing
        cls.fixed_now = datetime.datetime(2025, 6, 15, 10, 0, 0, tzinfo=datetime.timezone.utc)
        cls.fixed_local_date = datetime.date(2025, 6, 15) # Corresponds to a Sunday

        cls.patcher_now = patch('django.utils.timezone.now', return_value=cls.fixed_now)
        cls.mock_now = cls.patcher_now.start()

        # Create a ServiceSettings instance
        # The factory's _create method ensures only one instance (pk=1) exists
        cls.service_settings = ServiceSettingsFactory(
            drop_off_start_time=datetime.time(9, 0),
            drop_off_end_time=datetime.time(17, 0),
            drop_off_spacing_mins=30,
            latest_same_day_dropoff_time=datetime.time(12, 0), # Ensure it's within default range
        )

        # Create other related factory instances that might be needed by ServiceBookingFactory
        cls.service_profile = ServiceProfileFactory()
        cls.service_type = ServiceTypeFactory()
        cls.customer_motorcycle = CustomerMotorcycleFactory(service_profile=cls.service_profile)

    @classmethod
    def tearDownClass(cls):
        """
        Stop the patcher after all tests are done.
        """
        cls.patcher_now.stop()
        super().tearDownClass()

    def setUp(self):
        """
        Set up before each test to ensure a clean state for service_settings.
        """
        # Reload settings before each test to ensure any modifications by previous tests are reset
        self.service_settings.refresh_from_db()
        self.service_settings.drop_off_start_time = datetime.time(9, 0)
        self.service_settings.drop_off_end_time = datetime.time(17, 0)
        self.service_settings.drop_off_spacing_mins = 30
        self.service_settings.latest_same_day_dropoff_time = datetime.time(12, 0) # Reset to default
        self.service_settings.save() # Save to apply these default settings

        # Clear existing bookings before each test to ensure a clean slate
        ServiceBooking.objects.all().delete()


    def test_no_settings(self):
        """
        Test that an empty list is returned if no ServiceSettings exist.
        """
        ServiceSettings.objects.all().delete() # Delete all settings
        available_times = get_available_dropoff_times(datetime.date.today())
        self.assertEqual(available_times, [])

    def test_default_settings_no_bookings(self):
        """
        Test that default available times are generated with no existing bookings.
        For `fixed_local_date` (which is 'today' in mocked time), the latest_same_day_dropoff_time
        should limit the available slots.
        """
        # Default settings: 09:00-17:00, 30 min spacing, latest_same_day_dropoff_time = 12:00
        # Expected times for 'today' should be restricted to 12:00
        available_times = get_available_dropoff_times(self.fixed_local_date)
        expected_times = [
            "09:00", "09:30", "10:00", "10:30", "11:00", "11:30", "12:00"
        ]
        self.assertEqual(available_times, expected_times)

    def test_single_booking_blocks_slot(self):
        """
        Test that a single booking correctly blocks its own slot and surrounding slots
        based on drop_off_spacing_mins, and respects latest_same_day_dropoff_time.
        """
        # Booking at 10:00, 30 min spacing
        # Should block 09:30, 10:00, 10:30
        ServiceBookingFactory(
            service_profile=self.service_profile,
            service_type=self.service_type,
            customer_motorcycle=self.customer_motorcycle,
            dropoff_date=self.fixed_local_date,
            dropoff_time=datetime.time(10, 0),
        )

        available_times = get_available_dropoff_times(self.fixed_local_date)
        # Expected times, restricted to 12:00 by latest_same_day_dropoff_time
        expected_times = [
            "09:00",
            # "09:30", # Blocked by 10:00 booking
            # "10:00", # Blocked by itself
            # "10:30", # Blocked by 10:00 booking
            "11:00", "11:30", "12:00"
        ]
        self.assertEqual(available_times, expected_times)

    def test_multiple_bookings_block_slots(self):
        """
        Test that multiple bookings correctly block their respective slots,
        respecting latest_same_day_dropoff_time.
        """
        # Bookings at 09:30 and 11:00 (30 min spacing)
        # 09:30 booking blocks: 09:00, 09:30, 10:00
        # 11:00 booking blocks: 10:30, 11:00, 11:30
        ServiceBookingFactory(
            service_profile=self.service_profile,
            service_type=self.service_type,
            customer_motorcycle=self.customer_motorcycle,
            dropoff_date=self.fixed_local_date,
            dropoff_time=datetime.time(9, 30),
        )
        ServiceBookingFactory(
            service_profile=self.service_profile,
            service_type=self.service_type,
            customer_motorcycle=self.customer_motorcycle,
            dropoff_date=self.fixed_local_date,
            dropoff_time=datetime.time(11, 0),
        )

        available_times = get_available_dropoff_times(self.fixed_local_date)
        # Expected times, restricted to 12:00 by latest_same_day_dropoff_time
        expected_times = [
            # "09:00", # Blocked by 09:30 booking
            # "09:30", # Blocked by itself
            # "10:00", # Blocked by 09:30 booking
            # "10:30", # Blocked by 11:00 booking
            # "11:00", # Blocked by itself
            # "11:30", # Blocked by 11:00 booking
            "12:00"
        ]
        self.assertEqual(available_times, expected_times)

    def test_full_day_blocked_by_bookings(self):
        """
        Test a scenario where enough bookings exist to block all slots for the day,
        within the latest_same_day_dropoff_time constraint.
        """
        self.service_settings.drop_off_start_time = datetime.time(9, 0)
        self.service_settings.drop_off_end_time = datetime.time(10, 0)
        # Set latest_same_day_dropoff_time to be within these bounds for validation
        self.service_settings.latest_same_day_dropoff_time = datetime.time(10, 0)
        self.service_settings.drop_off_spacing_mins = 30
        self.service_settings.save()

        # Potential slots: 09:00, 09:30, 10:00 (after latest_same_day_dropoff_time adjustment)
        # Booking at 09:00 (blocks 09:00, 09:30)
        ServiceBookingFactory(
            service_profile=self.service_profile,
            service_type=self.service_type,
            customer_motorcycle=self.customer_motorcycle,
            dropoff_date=self.fixed_local_date,
            dropoff_time=datetime.time(9, 0),
        )
        # Booking at 10:00 (blocks 09:30, 10:00)
        ServiceBookingFactory(
            service_profile=self.service_profile,
            service_type=self.service_type,
            customer_motorcycle=self.customer_motorcycle,
            dropoff_date=self.fixed_local_date,
            dropoff_time=datetime.time(10, 0),
        )

        available_times = get_available_dropoff_times(self.fixed_local_date)
        self.assertEqual(available_times, []) # All slots should be blocked

    def test_start_and_end_times_inclusive(self):
        """
        Test that start_time and end_time slots are included if available,
        and latest_same_day_dropoff_time is respected.
        """
        self.service_settings.drop_off_start_time = datetime.time(10, 0)
        self.service_settings.drop_off_end_time = datetime.time(10, 0)
        self.service_settings.drop_off_spacing_mins = 30
        # Set latest_same_day_dropoff_time to be within these bounds for validation
        self.service_settings.latest_same_day_dropoff_time = datetime.time(10, 0)
        self.service_settings.save()

        available_times = get_available_dropoff_times(self.fixed_local_date)
        self.assertEqual(available_times, ["10:00"])

    def test_no_slots_if_start_after_end_time_within_interval(self):
        """
        Test that no slots are returned if the start_time is after the
        effective end_time (adjusted by latest_same_day_dropoff_time if applicable).
        This test now ensures valid settings for the ServiceSettings model.
        """
        self.service_settings.drop_off_start_time = datetime.time(10, 0)
        self.service_settings.drop_off_end_time = datetime.time(10, 30) # End time is after start
        self.service_settings.drop_off_spacing_mins = 30
        # Set latest_same_day_dropoff_time to cause no slots
        self.service_settings.latest_same_day_dropoff_time = datetime.time(9, 30)
        self.service_settings.save()

        # Given start_time is 10:00 and latest_same_day_dropoff_time is 9:30,
        # the effective end_time will become 9:30, which is before start_time.
        # This should result in no available slots.
        available_times = get_available_dropoff_times(self.fixed_local_date)
        self.assertEqual(available_times, [])


    def test_different_spacing(self):
        """
        Test that slots are generated correctly with a different spacing (e.g., 60 minutes),
        respecting latest_same_day_dropoff_time.
        """
        self.service_settings.drop_off_start_time = datetime.time(9, 0)
        self.service_settings.drop_off_end_time = datetime.time(12, 0)
        self.service_settings.drop_off_spacing_mins = 60
        self.service_settings.latest_same_day_dropoff_time = datetime.time(12, 0) # Maintain restriction
        self.service_settings.save()

        expected_times = ["09:00", "10:00", "11:00", "12:00"]
        available_times = get_available_dropoff_times(self.fixed_local_date)
        self.assertEqual(available_times, expected_times)

    def test_booking_on_another_day_does_not_block(self):
        """
        Test that bookings on different dates do not affect the current date's availability,
        and respects latest_same_day_dropoff_time for the current date.
        """
        ServiceBookingFactory(
            service_profile=self.service_profile,
            service_type=self.service_type,
            customer_motorcycle=self.customer_motorcycle,
            dropoff_date=self.fixed_local_date + datetime.timedelta(days=1), # Next day
            dropoff_time=datetime.time(10, 0),
        )

        available_times = get_available_dropoff_times(self.fixed_local_date)
        # Expected times are restricted to 12:00 due to latest_same_day_dropoff_time for fixed_local_date
        expected_times = [
            "09:00", "09:30", "10:00", "10:30", "11:00", "11:30", "12:00"
        ]
        self.assertEqual(available_times, expected_times)

    def test_overlap_between_start_and_end_times(self):
        """
        Test that potential slots are generated even if start/end times are very close,
        and latest_same_day_dropoff_time is respected.
        """
        self.service_settings.drop_off_start_time = datetime.time(9, 0)
        self.service_settings.drop_off_end_time = datetime.time(9, 15)
        self.service_settings.drop_off_spacing_mins = 30
        # Set latest_same_day_dropoff_time to be within these bounds for validation and effective range
        self.service_settings.latest_same_day_dropoff_time = datetime.time(9, 15)
        self.service_settings.save()

        # Only one 09:00 slot is possible, as 09:00 + 30mins (09:30) is past 09:15 end time.
        # This scenario is now correctly reflecting the new latest_same_day_dropoff_time.
        available_times = get_available_dropoff_times(self.fixed_local_date)
        self.assertEqual(available_times, ["09:00"])

    def test_very_small_spacing(self):
        """
        Test with very small spacing (e.g., 1 minute),
        and ensure latest_same_day_dropoff_time is respected.
        """
        self.service_settings.drop_off_start_time = datetime.time(9, 0)
        self.service_settings.drop_off_end_time = datetime.time(9, 5)
        self.service_settings.drop_off_spacing_mins = 1
        # Set latest_same_day_dropoff_time to allow the full 09:00-09:05 range for this test
        self.service_settings.latest_same_day_dropoff_time = datetime.time(9, 5)
        self.service_settings.save()

        expected_times = ["09:00", "09:01", "09:02", "09:03", "09:04", "09:05"]
        available_times = get_available_dropoff_times(self.fixed_local_date)
        self.assertEqual(available_times, expected_times)

        # Now add a booking in the middle to see its effect
        ServiceBookingFactory(
            service_profile=self.service_profile,
            service_type=self.service_type,
            customer_motorcycle=self.customer_motorcycle,
            dropoff_date=self.fixed_local_date,
            dropoff_time=datetime.time(9, 2), # This booking should block 09:01, 09:02, 09:03
        )
        # Re-assert spacing and save settings to ensure latest_same_day_dropoff_time is applied if needed
        self.service_settings.drop_off_spacing_mins = 1
        self.service_settings.latest_same_day_dropoff_time = datetime.time(9, 5) # Ensure it's still wide enough
        self.service_settings.save()

        expected_times_after_booking = ["09:00", "09:04", "09:05"]
        available_times_after_booking = get_available_dropoff_times(self.fixed_local_date)
        self.assertEqual(available_times_after_booking, expected_times_after_booking)

    def test_start_time_after_latest_same_day_dropoff(self):
        """
        Test that if selected_date is today, only slots before latest_same_day_dropoff_time
        are available.
        """
        # Ensure latest_same_day_dropoff_time is applied for today's date
        self.service_settings.drop_off_start_time = datetime.time(9, 0)
        self.service_settings.drop_off_end_time = datetime.time(17, 0)
        self.service_settings.drop_off_spacing_mins = 60
        self.service_settings.latest_same_day_dropoff_time = datetime.time(11, 0)
        self.service_settings.save()

        # Mock timezone.now to return self.fixed_now (which is fixed_local_date)
        with patch('django.utils.timezone.now', return_value=self.fixed_now):
            available_times = get_available_dropoff_times(self.fixed_local_date)
            # Since fixed_local_date is 'today' (mocked), only slots <= 11:00 should be available
            expected_times = ["09:00", "10:00", "11:00"]
            self.assertEqual(available_times, expected_times)

    def test_start_time_after_latest_same_day_dropoff_future_date(self):
        """
        Test that latest_same_day_dropoff_time is NOT applied for a future date.
        """
        self.service_settings.drop_off_start_time = datetime.time(9, 0)
        self.service_settings.drop_off_end_time = datetime.time(17, 0)
        self.service_settings.drop_off_spacing_mins = 60
        self.service_settings.latest_same_day_dropoff_time = datetime.time(11, 0)
        self.service_settings.save()

        future_date = self.fixed_local_date + datetime.timedelta(days=1)
        with patch('django.utils.timezone.now', return_value=self.fixed_now):
            available_times = get_available_dropoff_times(future_date)
            # For future dates, the latest_same_day_dropoff_time should not restrict
            expected_times = [
                "09:00", "10:00", "11:00", "12:00", "13:00", "14:00",
                "15:00", "16:00", "17:00"
            ]
            self.assertEqual(available_times, expected_times)
