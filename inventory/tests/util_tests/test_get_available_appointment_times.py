# inventory/tests/utils/test_get_available_appointment_times.py

from django.test import TestCase
from datetime import date, datetime, time, timedelta
from django.utils import timezone

from inventory.utils.get_available_appointment_times import get_available_appointment_times
from inventory.models import InventorySettings, SalesBooking
from ..test_helpers.model_factories import InventorySettingsFactory, SalesBookingFactory

class GetAvailableAppointmentTimesUtilTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Set up a base InventorySettings for common tests
        cls.inventory_settings = InventorySettingsFactory(
            sales_appointment_start_time=time(9, 0),  # 9:00 AM
            sales_appointment_end_time=time(17, 0),   # 5:00 PM
            sales_appointment_spacing_mins=30,      # 30-minute intervals
            min_advance_booking_hours=1             # 1 hour notice
        )
        cls.today = timezone.localdate(timezone.now())

    def test_no_inventory_settings(self):
        selected_date = self.today
        available_times = get_available_appointment_times(selected_date, None)
        self.assertEqual(available_times, [])

    def test_basic_time_slot_generation(self):
        # Test basic generation for a future date where min_advance_hours doesn't apply
        future_date = self.today + timedelta(days=7)
        available_times = get_available_appointment_times(future_date, self.inventory_settings)
        
        expected_times = [
            "09:00", "09:30", "10:00", "10:30", "11:00", "11:30",
            "12:00", "12:30", "13:00", "13:30", "14:00", "14:30",
            "15:00", "15:30", "16:00", "16:30", "17:00"
        ]
        self.assertEqual(available_times, expected_times)

    def test_excludes_times_too_soon_for_today(self):
        # Create settings where current time would exclude early slots today
        # Make start time 9:00, end 17:00, spacing 30 mins, min_advance 2 hours
        settings_today = InventorySettingsFactory(
            sales_appointment_start_time=time(9, 0),
            sales_appointment_end_time=time(17, 0),
            sales_appointment_spacing_mins=30,
            min_advance_booking_hours=2,
            pk=200 # Unique PK
        )

        # To reliably test "too soon", we need to know the current time when tests run.
        # Let's assume current time is 10:00 AM for calculation purposes.
        # Any time <= 12:00 PM (10:00 + 2 hours) should be excluded.
        # This is tricky with `timezone.now()`.
        # A more robust test would involve mocking `timezone.now()` or dynamically adjusting expected output.
        # For this test, we'll run it against the *actual* current time.
        
        now = timezone.now()
        earliest_valid_datetime = now + timedelta(hours=settings_today.min_advance_booking_hours)

        available_times = get_available_appointment_times(self.today, settings_today)
        
        # All returned times should be after earliest_valid_datetime
        for time_str in available_times:
            test_datetime = timezone.make_aware(datetime.combine(self.today, datetime.strptime(time_str, '%H:%M').time()), timezone=timezone.get_current_timezone())
            self.assertGreater(test_datetime, earliest_valid_datetime)

        # Check that times before earliest_valid_datetime are NOT in the list
        # We can't definitively pick a specific time to assert absence without mocking
        # so we rely on the above loop.

    def test_excludes_single_booked_slot(self):
        # Book an appointment for a specific time on a future date
        selected_date = self.today + timedelta(days=1)
        booked_time = time(10, 0) # Book 10:00 AM
        SalesBookingFactory(appointment_date=selected_date, appointment_time=booked_time, booking_status='confirmed')

        available_times = get_available_appointment_times(selected_date, self.inventory_settings)

        # 10:00 should be excluded due to direct booking
        self.assertNotIn("10:00", available_times)
        # Also, surrounding slots (9:30, 10:30) should be excluded due to 30 min spacing
        self.assertNotIn("09:30", available_times)
        self.assertNotIn("10:30", available_times)

        # Other times should still be present
        self.assertIn("09:00", available_times)
        self.assertIn("11:00", available_times)


    def test_excludes_multiple_booked_slots(self):
        selected_date = self.today + timedelta(days=2)
        SalesBookingFactory(appointment_date=selected_date, appointment_time=time(9, 30), booking_status='confirmed')
        SalesBookingFactory(appointment_date=selected_date, appointment_time=time(11, 0), booking_status='reserved') # Test 'reserved' status
        SalesBookingFactory(appointment_date=selected_date, appointment_time=time(15, 0), booking_status='confirmed')

        available_times = get_available_appointment_times(selected_date, self.inventory_settings)

        # 9:30 booked: excludes 9:00, 9:30, 10:00
        self.assertNotIn("09:00", available_times)
        self.assertNotIn("09:30", available_times)
        self.assertNotIn("10:00", available_times)

        # 11:00 booked: excludes 10:30, 11:00, 11:30
        self.assertNotIn("10:30", available_times)
        self.assertNotIn("11:00", available_times)
        self.assertNotIn("11:30", available_times)

        # 15:00 booked: excludes 14:30, 15:00, 15:30
        self.assertNotIn("14:30", available_times)
        self.assertNotIn("15:00", available_times)
        self.assertNotIn("15:30", available_times)

        # Ensure other times are still present
        self.assertIn("12:00", available_times)
        self.assertIn("13:00", available_times)
        self.assertIn("16:00", available_times)

    def test_booked_slot_with_different_status_does_not_block(self):
        selected_date = self.today + timedelta(days=3)
        # Create a booking that should NOT block (e.g., 'cancelled')
        SalesBookingFactory(appointment_date=selected_date, appointment_time=time(10, 0), booking_status='cancelled')
        
        available_times = get_available_appointment_times(selected_date, self.inventory_settings)
        
        # 10:00 should still be available because the booking is cancelled
        self.assertIn("10:00", available_times)
        self.assertIn("09:30", available_times) # Check surrounding as well
        self.assertIn("10:30", available_times)

    def test_bookings_on_different_date_do_not_block(self):
        selected_date = self.today + timedelta(days=4)
        # Book a time on a different date
        SalesBookingFactory(appointment_date=selected_date + timedelta(days=1), appointment_time=time(10, 0), booking_status='confirmed')

        available_times = get_available_appointment_times(selected_date, self.inventory_settings)
        
        # 10:00 should still be available for the selected_date
        self.assertIn("10:00", available_times)
