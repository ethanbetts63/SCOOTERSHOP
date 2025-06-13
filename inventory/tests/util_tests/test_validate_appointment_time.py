# inventory/tests/utils/test_validate_appointment_time.py

from django.test import TestCase
from datetime import date, datetime, time, timedelta
from django.utils import timezone

from inventory.utils.validate_appointment_time import validate_appointment_time
from inventory.models import InventorySettings
from ..test_helpers.model_factories import InventorySettingsFactory

class ValidateAppointmentTimeUtilTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.inventory_settings = InventorySettingsFactory(
            sales_appointment_start_time=time(9, 0),
            sales_appointment_end_time=time(17, 0),
            sales_appointment_spacing_mins=30,
            min_advance_booking_hours=2
        )

    def test_valid_time_within_range(self):
        future_date = date.today() + timedelta(days=7)
        valid_time = time(10, 0)
        # Pass an empty list for existing_booked_times as this test isn't about overlaps
        errors = validate_appointment_time(future_date, valid_time, self.inventory_settings, [])
        self.assertEqual(errors, [])

    def test_time_before_start_time(self):
        future_date = date.today() + timedelta(days=7)
        early_time = time(8, 0)
        errors = validate_appointment_time(future_date, early_time, self.inventory_settings, [])
        self.assertIn(
            f"Appointments are only available between {self.inventory_settings.sales_appointment_start_time.strftime('%I:%M %p')} and {self.inventory_settings.sales_appointment_end_time.strftime('%I:%M %p')}.",
            errors
        )
        self.assertEqual(len(errors), 1)

    def test_time_after_end_time(self):
        future_date = date.today() + timedelta(days=7)
        late_time = time(18, 0)
        errors = validate_appointment_time(future_date, late_time, self.inventory_settings, [])
        self.assertIn(
            f"Appointments are only available between {self.inventory_settings.sales_appointment_start_time.strftime('%I:%M %p')} and {self.inventory_settings.sales_appointment_end_time.strftime('%I:%M %p')}.",
            errors
        )
        self.assertEqual(len(errors), 1)

    def test_time_too_soon_for_today(self):
        today = date.today()
        now = timezone.now()
        
        # Calculate a time that is just within the min_advance_booking_hours
        # We need a time that is valid for operating hours but too close to now
        test_datetime_too_soon = now + timedelta(hours=self.inventory_settings.min_advance_booking_hours - 1)
        
        # Ensure test_time is within operating hours for this specific test
        # If the calculated 'too soon' time falls outside operating hours, adjust it
        test_time = test_datetime_too_soon.time()
        if not (self.inventory_settings.sales_appointment_start_time <= test_time <= self.inventory_settings.sales_appointment_end_time):
            # If `test_datetime_too_soon` is outside bounds, pick a time just inside
            # but ensure it's still "too soon" relative to `now`.
            # For simplicity, let's pick start_time if it's too soon, otherwise a minute after `now`.
            if datetime.combine(today, self.inventory_settings.sales_appointment_start_time) <= now + timedelta(hours=self.inventory_settings.min_advance_booking_hours):
                 test_time = self.inventory_settings.sales_appointment_start_time
            else: # Fallback if start_time isn't too soon itself
                 test_time = (now + timedelta(minutes=1)).time()
                 if test_time > self.inventory_settings.sales_appointment_end_time:
                     # If even a minute after now is past end time, can't test "too soon" for today
                     self.skipTest("Cannot find a 'too soon' time for today within operating hours.")

        errors = validate_appointment_time(today, test_time, self.inventory_settings, [])
        self.assertIn(
            f"The selected time is too soon. Appointments require at least {self.inventory_settings.min_advance_booking_hours} hours notice from the current time.",
            errors
        )
        self.assertEqual(len(errors), 1)
    
    def test_time_on_today_but_just_valid(self):
        today = date.today()
        now = timezone.now()
        
        # Calculate a time that is just past min_advance_booking_hours
        valid_datetime_candidate = now + timedelta(hours=self.inventory_settings.min_advance_booking_hours + 1)
        valid_time = valid_datetime_candidate.time()

        # Adjust to ensure it's within operating hours if the calculated time falls outside
        if not (self.inventory_settings.sales_appointment_start_time <= valid_time <= self.inventory_settings.sales_appointment_end_time):
            # If the calculated valid_time is outside, pick the earliest valid time
            # within operating hours that is also past min_advance_booking_hours.
            earliest_possible_time_obj = (now + timedelta(hours=self.inventory_settings.min_advance_booking_hours)).time()
            if earliest_possible_time_obj < self.inventory_settings.sales_appointment_start_time:
                valid_time = self.inventory_settings.sales_appointment_start_time
            else:
                valid_time = earliest_possible_time_obj

            if valid_time > self.inventory_settings.sales_appointment_end_time:
                self.skipTest("Cannot find a valid 'just valid' time for today's date within operating hours given current time and min_advance_booking_hours.")

        errors = validate_appointment_time(today, valid_time, self.inventory_settings, [])
        self.assertEqual(errors, [])


    def test_no_inventory_settings(self):
        test_date = date.today()
        test_time = time(10, 0)
        errors = validate_appointment_time(test_date, test_time, None, [])
        self.assertEqual(errors, [])

    def test_overlap_with_existing_booking(self):
        selected_date = date.today() + timedelta(days=7)
        spacing = self.inventory_settings.sales_appointment_spacing_mins # 30 mins
        
        # An existing booking at 10:00 AM
        existing_booked_times = [time(10, 0)]

        # Test a time that directly overlaps (10:00)
        errors = validate_appointment_time(selected_date, time(10, 0), self.inventory_settings, existing_booked_times)
        self.assertIn("The selected time (10:00) overlaps with an existing appointment.", errors)
        self.assertEqual(len(errors), 1)

        # Test a time that overlaps due to spacing (9:30, 30 mins before 10:00)
        errors = validate_appointment_time(selected_date, time(9, 30), self.inventory_settings, existing_booked_times)
        self.assertIn("The selected time (09:30) overlaps with an existing appointment.", errors)
        self.assertEqual(len(errors), 1)

        # Test a time that overlaps due to spacing (10:30, 30 mins after 10:00)
        errors = validate_appointment_time(selected_date, time(10, 30), self.inventory_settings, existing_booked_times)
        self.assertIn("The selected time (10:30) overlaps with an existing appointment.", errors)
        self.assertEqual(len(errors), 1)

    def test_no_overlap_with_existing_booking(self):
        selected_date = date.today() + timedelta(days=7)
        
        # An existing booking at 10:00 AM with 30 min spacing
        existing_booked_times = [time(10, 0)]

        # Test a time that is clearly outside the overlap window (e.g., 9:00, 11:00)
        errors = validate_appointment_time(selected_date, time(9, 0), self.inventory_settings, existing_booked_times)
        self.assertEqual(errors, [])

        errors = validate_appointment_time(selected_date, time(11, 0), self.inventory_settings, existing_booked_times)
        self.assertEqual(errors, [])

    def test_multiple_overlaps(self):
        selected_date = date.today() + timedelta(days=7)
        existing_booked_times = [time(10, 0), time(11, 0)] # Bookings at 10:00 and 11:00

        # Test a time that overlaps with the first booking (10:30)
        errors = validate_appointment_time(selected_date, time(10, 30), self.inventory_settings, existing_booked_times)
        self.assertIn("The selected time (10:30) overlaps with an existing appointment.", errors)
        self.assertEqual(len(errors), 1) # Only one error should be added

        # Test a time that is valid
        errors = validate_appointment_time(selected_date, time(12, 0), self.inventory_settings, existing_booked_times)
        self.assertEqual(errors, [])
