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

        # Create base related objects for ServiceBookingFactory
        cls.service_profile = ServiceProfileFactory()
        cls.service_type = ServiceTypeFactory()
        cls.customer_motorcycle = CustomerMotorcycleFactory(service_profile=cls.service_profile)

    @classmethod
    def tearDownClass(cls):
        """
        Clean up mocks after all tests are done.
        """
        cls.patcher_now.stop()
        super().tearDownClass()

    def setUp(self):
        """
        Set up for each test method. Clear existing data and create fresh ServiceSettings.
        """
        ServiceSettings.objects.all().delete()
        ServiceBooking.objects.all().delete()

        # Create a default ServiceSettings for each test, can be overridden
        self.service_settings = ServiceSettingsFactory(
            drop_off_start_time=datetime.time(9, 0),
            drop_off_end_time=datetime.time(17, 0),
            drop_off_spacing_mins=30
        )

    def test_no_service_settings(self):
        """
        Test that an empty list is returned if no ServiceSettings exist.
        """
        ServiceSettings.objects.all().delete() # Remove the settings created in setUp
        available_times = get_available_dropoff_times(self.fixed_local_date)
        self.assertEqual(available_times, [])

    def test_basic_availability_no_bookings(self):
        """
        Test that all slots are available when there are no existing bookings.
        Default settings: 9:00 - 17:00, 30 min spacing.
        """
        expected_times = [
            "09:00", "09:30", "10:00", "10:30", "11:00", "11:30",
            "12:00", "12:30", "13:00", "13:30", "14:00", "14:30",
            "15:00", "15:30", "16:00", "16:30", "17:00"
        ]
        available_times = get_available_dropoff_times(self.fixed_local_date)
        self.assertEqual(available_times, expected_times)

    def test_different_spacing_minutes(self):
        """
        Test with different drop-off spacing minutes.
        """
        self.service_settings.drop_off_spacing_mins = 60 # 1 hour spacing
        self.service_settings.save()

        expected_times = [
            "09:00", "10:00", "11:00", "12:00", "13:00", "14:00",
            "15:00", "16:00", "17:00"
        ]
        available_times = get_available_dropoff_times(self.fixed_local_date)
        self.assertEqual(available_times, expected_times)

        self.service_settings.drop_off_spacing_mins = 15 # 15 min spacing
        self.service_settings.save()

        expected_times_15min = [
            "09:00", "09:15", "09:30", "09:45", "10:00", "10:15", "10:30", "10:45",
            "11:00", "11:15", "11:30", "11:45", "12:00", "12:15", "12:30", "12:45",
            "13:00", "13:15", "13:30", "13:45", "14:00", "14:15", "14:30", "14:45",
            "15:00", "15:15", "15:30", "15:45", "16:00", "16:15", "16:30", "16:45",
            "17:00"
        ]
        available_times = get_available_dropoff_times(self.fixed_local_date)
        self.assertEqual(available_times, expected_times_15min)

    def test_different_start_and_end_times(self):
        """
        Test with different start and end times for drop-offs.
        """
        self.service_settings.drop_off_start_time = datetime.time(10, 0)
        self.service_settings.drop_off_end_time = datetime.time(14, 0)
        self.service_settings.drop_off_spacing_mins = 60
        self.service_settings.save()

        expected_times = [
            "10:00", "11:00", "12:00", "13:00", "14:00"
        ]
        available_times = get_available_dropoff_times(self.fixed_local_date)
        self.assertEqual(available_times, expected_times)

    def test_single_slot_duration(self):
        """
        Test when start and end times allow only one slot.
        Adjusted end time to pass model validation.
        """
        self.service_settings.drop_off_start_time = datetime.time(12, 0)
        self.service_settings.drop_off_end_time = datetime.time(12, 1) # Set to 12:01 to pass validation
        self.service_settings.drop_off_spacing_mins = 30
        self.service_settings.save()

        expected_times = ["12:00"]
        available_times = get_available_dropoff_times(self.fixed_local_date)
        self.assertEqual(available_times, expected_times)

    def test_single_booking_blocks_slots(self):
        """
        Test that a single booking correctly blocks its slot and surrounding slots.
        Booking at 10:00 with 30 min spacing should block 09:30, 10:00, 10:30.
        """
        # Create a booking at 10:00
        ServiceBookingFactory(
            service_profile=self.service_profile,
            service_type=self.service_type,
            customer_motorcycle=self.customer_motorcycle,
            dropoff_date=self.fixed_local_date,
            dropoff_time=datetime.time(10, 0),
            booking_status='confirmed' # This status counts for blocking
        )

        expected_times = [
            "09:00", "11:00", "11:30", "12:00", "12:30", "13:00", "13:30",
            "14:00", "14:30", "15:00", "15:30", "16:00", "16:30", "17:00"
        ]
        available_times = get_available_dropoff_times(self.fixed_local_date)
        self.assertEqual(available_times, expected_times)
        self.assertNotIn("09:30", available_times)
        self.assertNotIn("10:00", available_times)
        self.assertNotIn("10:30", available_times)

    def test_multiple_bookings_block_slots(self):
        """
        Test that multiple bookings correctly block their respective slots.
        Bookings at 10:00 and 14:00 with 30 min spacing.
        """
        # Booking 1: 10:00 (blocks 09:30, 10:00, 10:30)
        ServiceBookingFactory(
            service_profile=self.service_profile,
            service_type=self.service_type,
            customer_motorcycle=self.customer_motorcycle,
            dropoff_date=self.fixed_local_date,
            dropoff_time=datetime.time(10, 0),
            booking_status='booked'
        )
        # Booking 2: 14:00 (blocks 13:30, 14:00, 14:30)
        ServiceBookingFactory(
            service_profile=self.service_profile,
            service_type=self.service_type,
            customer_motorcycle=self.customer_motorcycle,
            dropoff_date=self.fixed_local_date,
            dropoff_time=datetime.time(14, 0),
            booking_status='in_progress'
        )

        expected_times = [
            "09:00", "11:00", "11:30", "12:00", "12:30", "13:00",
            "15:00", "15:30", "16:00", "16:30", "17:00"
        ]
        available_times = get_available_dropoff_times(self.fixed_local_date)
        self.assertEqual(available_times, expected_times)
        self.assertNotIn("09:30", available_times)
        self.assertNotIn("10:00", available_times)
        self.assertNotIn("10:30", available_times)
        self.assertNotIn("13:30", available_times)
        self.assertNotIn("14:00", available_times)
        self.assertNotIn("14:30", available_times)


    def test_bookings_near_start_and_end(self):
        """
        Test bookings at the very beginning and end of the operational hours.
        Spacing 30 mins:
        Booking at 09:00 should block 09:00 and 09:30.
        Booking at 17:00 should block 16:30 and 17:00.
        """
        self.service_settings.drop_off_start_time = datetime.time(9, 0)
        self.service_settings.drop_off_end_time = datetime.time(17, 0)
        self.service_settings.drop_off_spacing_mins = 30
        self.service_settings.save()

        # Booking exactly at start time
        ServiceBookingFactory(
            service_profile=self.service_profile,
            service_type=self.service_type,
            customer_motorcycle=self.customer_motorcycle,
            dropoff_date=self.fixed_local_date,
            dropoff_time=datetime.time(9, 0),
            booking_status='booked'
        )
        # Booking exactly at end time
        ServiceBookingFactory(
            service_profile=self.service_profile,
            service_type=self.service_type,
            customer_motorcycle=self.customer_motorcycle,
            dropoff_date=self.fixed_local_date,
            dropoff_time=datetime.time(17, 0),
            booking_status='booked'
        )

        # Expected times: all original slots except 09:00, 09:30, 16:30, 17:00
        expected_times = [
            "10:00", "10:30", "11:00", "11:30",
            "12:00", "12:30", "13:00", "13:30", "14:00", "14:30",
            "15:00", "15:30", "16:00"
        ]
        available_times = get_available_dropoff_times(self.fixed_local_date)
        self.assertEqual(available_times, expected_times)


    def test_non_blocking_booking_statuses(self):
        """
        Test that bookings with 'pending' or 'cancelled' status do NOT block slots.
        """
        # Create bookings that should NOT block
        ServiceBookingFactory(
            service_profile=self.service_profile,
            service_type=self.service_type,
            customer_motorcycle=self.customer_motorcycle,
            dropoff_date=self.fixed_local_date,
            dropoff_time=datetime.time(10, 0),
            booking_status='pending'
        )
        ServiceBookingFactory(
            service_profile=self.service_profile,
            service_type=self.service_type,
            customer_motorcycle=self.customer_motorcycle,
            dropoff_date=self.fixed_local_date,
            dropoff_time=datetime.time(14, 30),
            booking_status='cancelled'
        )
        ServiceBookingFactory(
            service_profile=self.service_profile,
            service_type=self.service_type,
            customer_motorcycle=self.customer_motorcycle,
            dropoff_date=self.fixed_local_date,
            dropoff_time=datetime.time(11, 30),
            booking_status='declined'
        )
        ServiceBookingFactory(
            service_profile=self.service_profile,
            service_type=self.service_type,
            customer_motorcycle=self.customer_motorcycle,
            dropoff_date=self.fixed_local_date,
            dropoff_time=datetime.time(12, 0),
            booking_status='no_show'
        )
        ServiceBookingFactory(
            service_profile=self.service_profile,
            service_type=self.service_type,
            customer_motorcycle=self.customer_motorcycle,
            dropoff_date=self.fixed_local_date,
            dropoff_time=datetime.time(13, 0),
            booking_status='completed'
        )
        ServiceBookingFactory(
            service_profile=self.service_profile,
            service_type=self.service_type,
            customer_motorcycle=self.customer_motorcycle,
            dropoff_date=self.fixed_local_date,
            dropoff_time=datetime.time(15, 0),
            booking_status='DECLINED_REFUNDED'
        )

        # Expected times should be all available slots as none of the bookings should block
        expected_times = [
            "09:00", "09:30", "10:00", "10:30", "11:00", "11:30",
            "12:00", "12:30", "13:00", "13:30", "14:00", "14:30",
            "15:00", "15:30", "16:00", "16:30", "17:00"
        ]
        available_times = get_available_dropoff_times(self.fixed_local_date)
        self.assertEqual(available_times, expected_times)


    def test_full_day_blocked_by_bookings(self):
        """
        Test a scenario where enough bookings exist to block all slots for the day.
        """
        self.service_settings.drop_off_start_time = datetime.time(9, 0)
        self.service_settings.drop_off_end_time = datetime.time(10, 0)
        self.service_settings.drop_off_spacing_mins = 30 # Slots: 09:00, 09:30, 10:00
        self.service_settings.save()

        # Create booking at 09:00 (blocks 09:00, 09:30)
        ServiceBookingFactory(
            service_profile=self.service_profile,
            service_type=self.service_type,
            customer_motorcycle=self.customer_motorcycle,
            dropoff_date=self.fixed_local_date,
            dropoff_time=datetime.time(9, 0),
            booking_status='booked'
        )
        # Create booking at 10:00 (blocks 09:30, 10:00)
        ServiceBookingFactory(
            service_profile=self.service_profile,
            service_type=self.service_type,
            customer_motorcycle=self.customer_motorcycle,
            dropoff_date=self.fixed_local_date,
            dropoff_time=datetime.time(10, 0),
            booking_status='confirmed'
        )

        # All slots should be blocked
        available_times = get_available_dropoff_times(self.fixed_local_date)
        self.assertEqual(available_times, [])

    def test_selected_date_is_different_day(self):
        """
        Test that bookings on a different date do not affect availability for the selected date.
        """
        future_date = self.fixed_local_date + datetime.timedelta(days=7) # A week from fixed_local_date

        # Create a booking on a future date
        ServiceBookingFactory(
            service_profile=self.service_profile,
            service_type=self.service_type,
            customer_motorcycle=self.customer_motorcycle,
            dropoff_date=future_date,
            dropoff_time=datetime.time(10, 0),
            booking_status='booked'
        )

        # Check availability for fixed_local_date (today) - should be unaffected
        expected_times = [
            "09:00", "09:30", "10:00", "10:30", "11:00", "11:30",
            "12:00", "12:30", "13:00", "13:30", "14:00", "14:30",
            "15:00", "15:30", "16:00", "16:30", "17:00"
        ]
        available_times = get_available_dropoff_times(self.fixed_local_date)
        self.assertEqual(available_times, expected_times)

        # Check availability for the future_date - it should be affected
        expected_times_future = [
            "09:00", "11:00", "11:30", "12:00", "12:30", "13:00", "13:30",
            "14:00", "14:30", "15:00", "15:30", "16:00", "16:30", "17:00"
        ]
        available_times_future = get_available_dropoff_times(future_date)
        self.assertEqual(available_times_future, expected_times_future)

    def test_overlap_between_start_and_end_times(self):
        """
        Test that potential slots are generated even if start/end times are very close.
        e.g., 9:00 to 9:15 with 30 min spacing -> only 9:00 as a potential starting point.
        e.g., 9:00 to 9:30 with 30 min spacing -> 9:00, 9:30.
        """
        self.service_settings.drop_off_start_time = datetime.time(9, 0)
        self.service_settings.drop_off_end_time = datetime.time(9, 15)
        self.service_settings.drop_off_spacing_mins = 30
        self.service_settings.save()

        # Only 09:00 should be the first valid candidate slot based on start time
        # With 30 min spacing, no other slots will be generated after it within the 09:15 end time.
        available_times = get_available_dropoff_times(self.fixed_local_date)
        self.assertEqual(available_times, ["09:00"]) 

        self.service_settings.drop_off_start_time = datetime.time(9, 0)
        self.service_settings.drop_off_end_time = datetime.time(9, 30)
        self.service_settings.drop_off_spacing_mins = 30
        self.service_settings.save()

        available_times = get_available_dropoff_times(self.fixed_local_date)
        self.assertEqual(available_times, ["09:00", "09:30"])

    def test_very_small_spacing(self):
        """
        Test with very small spacing (e.g., 1 minute).
        """
        self.service_settings.drop_off_start_time = datetime.time(9, 0)
        self.service_settings.drop_off_end_time = datetime.time(9, 5)
        self.service_settings.drop_off_spacing_mins = 1
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
            dropoff_time=datetime.time(9, 2),
            booking_status='booked'
        )
        # Booking at 09:02, spacing 1 min, blocks 09:01, 09:02, 09:03
        expected_times_blocked = ["09:00", "09:04", "09:05"]
        available_times_blocked = get_available_dropoff_times(self.fixed_local_date)
        self.assertEqual(available_times_blocked, expected_times_blocked)

