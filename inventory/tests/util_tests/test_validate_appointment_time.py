# inventory/tests/utils/test_validate_appointment_time.py

from django.test import TestCase
from datetime import date, datetime, time, timedelta
from django.utils import timezone
from unittest.mock import patch # Import patch

from inventory.utils.validate_appointment_time import validate_appointment_time
from inventory.models import InventorySettings
from ..test_helpers.model_factories import InventorySettingsFactory

class ValidateAppointmentTimeUtilTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.inventory_settings = InventorySettingsFactory(
            sales_appointment_start_time=time(9, 0),  # 9:00 AM
            sales_appointment_end_time=time(17, 0),   # 5:00 PM
            sales_appointment_spacing_mins=30,      # 30-minute intervals
            min_advance_booking_hours=2             # 2 hours notice
        )
        # We will dynamically set `cls.today` based on mocked `now` for each test.

    @patch('django.utils.timezone.now')
    def test_time_too_soon_for_today(self, mock_now):
        # Mock current time to be 10:00 AM on a specific date (e.g., June 15, 2025)
        # This allows us to predict what "too soon" means.
        fixed_now = datetime(2025, 6, 15, 10, 0, 0, tzinfo=timezone.get_current_timezone())
        mock_now.return_value = fixed_now

        today = fixed_now.date() # The date the mock `now` corresponds to

        # min_advance_hours is 2. So anything at or before 12:00 PM (10:00 + 2 hours) should be too soon.
        too_soon_time = time(11, 30) # Within operating hours, but before 12:00 PM
        
        errors = validate_appointment_time(today, too_soon_time, self.inventory_settings, [])
        self.assertIn(
            f"The selected time is too soon. Appointments require at least {self.inventory_settings.min_advance_booking_hours} hours notice from the current time.",
            errors
        )
        self.assertEqual(len(errors), 1)

        # Test another too soon time, just at the boundary
        too_soon_time_boundary = time(12, 0)
        errors = validate_appointment_time(today, too_soon_time_boundary, self.inventory_settings, [])
        self.assertIn(
            f"The selected time is too soon. Appointments require at least {self.inventory_settings.min_advance_booking_hours} hours notice from the current time.",
            errors
        )
        self.assertEqual(len(errors), 1)


    @patch('django.utils.timezone.now')
    def test_time_on_today_but_just_valid(self, mock_now):
        # Mock current time to be 10:00 AM on a specific date
        fixed_now = datetime(2025, 6, 15, 10, 0, 0, tzinfo=timezone.get_current_timezone())
        mock_now.return_value = fixed_now

        today = fixed_now.date()
        
        # min_advance_hours is 2. So anything after 12:00 PM should be valid.
        just_valid_time = time(12, 1) # Just after 12:00 PM, within operating hours
        
        errors = validate_appointment_time(today, just_valid_time, self.inventory_settings, [])
        self.assertEqual(errors, [])

        # Another valid time, further into the afternoon
        another_valid_time = time(15, 0)
        errors = validate_appointment_time(today, another_valid_time, self.inventory_settings, [])
        self.assertEqual(errors, [])


    def test_valid_time_within_range(self):
        # This test doesn't depend on `now`, so no mocking needed
        future_date = date(2025, 7, 1) # Fixed future date
        valid_time = time(10, 0)
        errors = validate_appointment_time(future_date, valid_time, self.inventory_settings, [])
        self.assertEqual(errors, [])

    def test_time_before_start_time(self):
        future_date = date(2025, 7, 1)
        early_time = time(8, 0)
        errors = validate_appointment_time(future_date, early_time, self.inventory_settings, [])
        self.assertIn(
            f"Appointments are only available between {self.inventory_settings.sales_appointment_start_time.strftime('%I:%M %p')} and {self.inventory_settings.sales_appointment_end_time.strftime('%I:%M %p')}.",
            errors
        )
        self.assertEqual(len(errors), 1)

    def test_time_after_end_time(self):
        future_date = date(2025, 7, 1)
        late_time = time(18, 0)
        errors = validate_appointment_time(future_date, late_time, self.inventory_settings, [])
        self.assertIn(
            f"Appointments are only available between {self.inventory_settings.sales_appointment_start_time.strftime('%I:%M %p')} and {self.inventory_settings.sales_appointment_end_time.strftime('%I:%M %p')}.",
            errors
        )
        self.assertEqual(len(errors), 1)


    def test_no_inventory_settings(self):
        test_date = date.today()
        test_time = time(10, 0)
        errors = validate_appointment_time(test_date, test_time, None, [])
        self.assertEqual(errors, [])

    def test_overlap_with_existing_booking(self):
        selected_date = date(2025, 7, 1)
        
        existing_booked_times = [time(10, 0)] # An existing booking at 10:00 AM

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
        selected_date = date(2025, 7, 1)
        
        existing_booked_times = [time(10, 0)]

        # Test a time that is clearly outside the overlap window (e.g., 9:00, 11:00)
        errors = validate_appointment_time(selected_date, time(9, 0), self.inventory_settings, existing_booked_times)
        self.assertEqual(errors, [])

        errors = validate_appointment_time(selected_date, time(11, 0), self.inventory_settings, existing_booked_times)
        self.assertEqual(errors, [])

    def test_multiple_overlaps(self):
        selected_date = date(2025, 7, 1)
        existing_booked_times = [time(10, 0), time(11, 0)]

        # Test a time that overlaps with the first booking (10:30)
        errors = validate_appointment_time(selected_date, time(10, 30), self.inventory_settings, existing_booked_times)
        self.assertIn("The selected time (10:30) overlaps with an existing appointment.", errors)
        self.assertEqual(len(errors), 1)

        # Test a time that is valid
        errors = validate_appointment_time(selected_date, time(12, 0), self.inventory_settings, existing_booked_times)
        self.assertEqual(errors, [])
