# inventory/tests/utils/test_validate_appointment_time.py

from django.test import TestCase
from datetime import date, datetime, time, timedelta

from inventory.utils.validate_appointment_time import validate_appointment_time
from inventory.models import InventorySettings
from ..test_helpers.model_factories import InventorySettingsFactory

class ValidateAppointmentTimeUtilTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Create an InventorySettings instance for testing
        cls.inventory_settings = InventorySettingsFactory(
            sales_appointment_start_time=time(9, 0), # 9 AM
            sales_appointment_end_time=time(17, 0), # 5 PM
            min_advance_booking_hours=2 # 2 hours notice
        )

    def test_valid_time_within_range(self):
        # Test a valid time within the operating hours for a future date
        future_date = date.today() + timedelta(days=7)
        valid_time = time(10, 0) # 10 AM, within 9 AM - 5 PM
        errors = validate_appointment_time(future_date, valid_time, self.inventory_settings)
        self.assertEqual(errors, [])

    def test_time_before_start_time(self):
        # Test a time before the sales_appointment_start_time
        future_date = date.today() + timedelta(days=7)
        early_time = time(8, 0) # 8 AM
        errors = validate_appointment_time(future_date, early_time, self.inventory_settings)
        self.assertIn(
            f"Appointments are only available between {self.inventory_settings.sales_appointment_start_time.strftime('%I:%M %p')} and {self.inventory_settings.sales_appointment_end_time.strftime('%I:%M %p')}.",
            errors
        )
        self.assertEqual(len(errors), 1)

    def test_time_after_end_time(self):
        # Test a time after the sales_appointment_end_time
        future_date = date.today() + timedelta(days=7)
        late_time = time(18, 0) # 6 PM
        errors = validate_appointment_time(future_date, late_time, self.inventory_settings)
        self.assertIn(
            f"Appointments are only available between {self.inventory_settings.sales_appointment_start_time.strftime('%I:%M %p')} and {self.inventory_settings.sales_appointment_end_time.strftime('%I:%M %p')}.",
            errors
        )
        self.assertEqual(len(errors), 1)

    def test_time_too_soon_for_today(self):
        # Test a time on the current date that is within min_advance_booking_hours
        today = date.today()
        
        # Calculate a time that is just within the min_advance_booking_hours
        current_datetime = datetime.now()
        too_soon_datetime = current_datetime + timedelta(hours=self.inventory_settings.min_advance_booking_hours - 1)
        
        # If the date rolls over, this test case isn't relevant for 'today's time'
        if too_soon_datetime.date() > today:
            # If the calculated 'too soon' time actually falls on a future date,
            # we need a time that is still on today's date but too early.
            # E.g., if now is 4 PM and min_advance is 2 hours, 5 PM today is too soon.
            # But if min_advance is 10 hours, 5 PM today is also too soon, but the target
            # for `earliest_allowed_datetime` would be tomorrow.
            # We want to test a time that is valid for the operating hours, but too close to 'now'.
            test_time = (current_datetime + timedelta(minutes=30)).time() # 30 mins from now
        else:
            test_time = too_soon_datetime.time()

        # Ensure test_time is within operating hours for this specific test
        if not (self.inventory_settings.sales_appointment_start_time <= test_time <= self.inventory_settings.sales_appointment_end_time):
            # If the calculated test_time falls outside operating hours,
            # pick a time just inside the operating hours but still too soon
            # relative to current time.
            test_time = self.inventory_settings.sales_appointment_start_time
            if datetime.combine(today, test_time) <= current_datetime + timedelta(hours=self.inventory_settings.min_advance_booking_hours):
                 pass # This time is indeed too soon.
            else:
                 # If even the start time isn't too soon, create a mock time that is.
                 # This can happen if start time is late, e.g., 9am and now is 8am, min_advance 2 hours -> 10am.
                 # So 9am is too soon.
                 # A more robust way to get a "too soon" time for today:
                 # It's simply any time that is earlier than (now + min_advance_hours).time()
                 if current_datetime.time() < self.inventory_settings.sales_appointment_end_time:
                    # Pick time just after current time, but before earliest allowed.
                    test_time = (current_datetime + timedelta(minutes=1)).time()
                 else: # If current time is already after end_time, then no time today is valid for this test.
                    # This implies the appointment date should be next day.
                    # In this specific test, we *force* today's date, so we need a time that is
                    # strictly too soon relative to now.
                    test_time = self.inventory_settings.sales_appointment_start_time
                    if test_time < current_datetime.time(): # If start time already passed today
                        test_time = (current_datetime + timedelta(minutes=1)).time()
                    
        
        errors = validate_appointment_time(today, test_time, self.inventory_settings)
        self.assertIn(
            f"The selected time is too soon. Appointments require at least {self.inventory_settings.min_advance_booking_hours} hours notice from the current time.",
            errors
        )
        self.assertEqual(len(errors), 1)

    def test_no_inventory_settings(self):
        # Test with no inventory settings provided (should return no errors)
        test_date = date.today()
        test_time = time(10, 0)
        errors = validate_appointment_time(test_date, test_time, None)
        self.assertEqual(errors, [])
