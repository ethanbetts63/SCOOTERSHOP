from django.test import TestCase
from datetime import date, datetime, time
from django.utils import timezone
from unittest.mock import patch

from inventory.utils.validate_appointment_time import validate_appointment_time


from inventory.tests.test_helpers.model_factories import InventorySettingsFactory


class ValidateAppointmentTimeUtilTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.inventory_settings = InventorySettingsFactory(
            sales_appointment_start_time=time(9, 0),
            sales_appointment_end_time=time(17, 0),
            sales_appointment_spacing_mins=30,
            min_advance_booking_hours=2,
        )

    @patch("django.utils.timezone.now")
    def test_time_on_today_but_just_valid(self, mock_now):
        fixed_now = datetime(
            2025, 6, 15, 10, 0, 0, tzinfo=timezone.get_current_timezone()
        )
        mock_now.return_value = fixed_now

        today = fixed_now.date()
        just_valid_time = time(12, 1)

        errors = validate_appointment_time(
            today, just_valid_time, self.inventory_settings, []
        )
        self.assertEqual(errors, [])

        another_valid_time = time(15, 0)
        errors = validate_appointment_time(
            today, another_valid_time, self.inventory_settings, []
        )
        self.assertEqual(errors, [])

    @patch("django.utils.timezone.now")
    def test_valid_time_within_range(self, mock_now):
        mock_now.return_value = datetime(
            2025, 6, 15, 10, 0, 0, tzinfo=timezone.get_current_timezone()
        )
        future_date = date(2025, 7, 1)
        valid_time = time(10, 0)
        errors = validate_appointment_time(
            future_date, valid_time, self.inventory_settings, []
        )
        self.assertEqual(errors, [])

    @patch("django.utils.timezone.now")
    def test_time_before_start_time(self, mock_now):
        mock_now.return_value = datetime(
            2025, 6, 15, 10, 0, 0, tzinfo=timezone.get_current_timezone()
        )
        future_date = date(2025, 7, 1)
        early_time = time(8, 0)
        errors = validate_appointment_time(
            future_date, early_time, self.inventory_settings, []
        )
        self.assertIn(
            f"Appointments are only available between {self.inventory_settings.sales_appointment_start_time.strftime('%I:%M %p')} and {self.inventory_settings.sales_appointment_end_time.strftime('%I:%M %p')}.",
            errors,
        )
        self.assertEqual(len(errors), 1)

    @patch("django.utils.timezone.now")
    def test_time_after_end_time(self, mock_now):
        mock_now.return_value = datetime(
            2025, 6, 15, 10, 0, 0, tzinfo=timezone.get_current_timezone()
        )
        future_date = date(2025, 7, 1)
        late_time = time(18, 0)
        errors = validate_appointment_time(
            future_date, late_time, self.inventory_settings, []
        )
        self.assertIn(
            f"Appointments are only available between {self.inventory_settings.sales_appointment_start_time.strftime('%I:%M %p')} and {self.inventory_settings.sales_appointment_end_time.strftime('%I:%M %p')}.",
            errors,
        )
        self.assertEqual(len(errors), 1)

    def test_no_inventory_settings(self):
        test_date = date.today()
        test_time = time(10, 0)
        errors = validate_appointment_time(test_date, test_time, None, [])
        self.assertEqual(errors, [])

    @patch("django.utils.timezone.now")
    def test_overlap_with_existing_booking(self, mock_now):
        mock_now.return_value = datetime(
            2025, 6, 15, 10, 0, 0, tzinfo=timezone.get_current_timezone()
        )
        selected_date = date(2025, 7, 1)

        existing_booked_times = [time(10, 0)]

        errors = validate_appointment_time(
            selected_date, time(10, 0), self.inventory_settings, existing_booked_times
        )
        self.assertIn(
            "The selected time (10:00) overlaps with an existing appointment.", errors
        )
        self.assertEqual(len(errors), 1)

        errors = validate_appointment_time(
            selected_date, time(9, 30), self.inventory_settings, existing_booked_times
        )
        self.assertIn(
            "The selected time (09:30) overlaps with an existing appointment.", errors
        )
        self.assertEqual(len(errors), 1)

        errors = validate_appointment_time(
            selected_date, time(10, 30), self.inventory_settings, existing_booked_times
        )
        self.assertIn(
            "The selected time (10:30) overlaps with an existing appointment.", errors
        )
        self.assertEqual(len(errors), 1)

    @patch("django.utils.timezone.now")
    def test_no_overlap_with_existing_booking(self, mock_now):
        mock_now.return_value = datetime(
            2025, 6, 15, 10, 0, 0, tzinfo=timezone.get_current_timezone()
        )
        selected_date = date(2025, 7, 1)

        existing_booked_times = [time(10, 0)]

        errors = validate_appointment_time(
            selected_date, time(9, 0), self.inventory_settings, existing_booked_times
        )
        self.assertEqual(errors, [])

        errors = validate_appointment_time(
            selected_date, time(11, 0), self.inventory_settings, existing_booked_times
        )
        self.assertEqual(errors, [])

    @patch("django.utils.timezone.now")
    def test_multiple_overlaps(self, mock_now):
        mock_now.return_value = datetime(
            2025, 6, 15, 10, 0, 0, tzinfo=timezone.get_current_timezone()
        )
        selected_date = date(2025, 7, 1)
        existing_booked_times = [time(10, 0), time(11, 0)]

        errors = validate_appointment_time(
            selected_date, time(10, 30), self.inventory_settings, existing_booked_times
        )
        self.assertIn(
            "The selected time (10:30) overlaps with an existing appointment.", errors
        )
        self.assertEqual(len(errors), 1)

        errors = validate_appointment_time(
            selected_date, time(12, 0), self.inventory_settings, existing_booked_times
        )
        self.assertEqual(errors, [])
