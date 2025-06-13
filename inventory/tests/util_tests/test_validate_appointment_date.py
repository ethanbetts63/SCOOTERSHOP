# inventory/tests/utils/test_validate_appointment_date.py

from django.test import TestCase
from datetime import date, datetime, time, timedelta

from inventory.utils.validate_appointment_date import validate_appointment_date
from inventory.models import InventorySettings
from ..test_helpers.model_factories import InventorySettingsFactory

class ValidateAppointmentDateUtilTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Create an InventorySettings instance for testing
        cls.inventory_settings = InventorySettingsFactory(
            sales_booking_open_days="Mon,Tue,Wed,Thu,Fri", # Mon-Fri
            sales_appointment_start_time=time(9, 0),
            sales_appointment_end_time=time(17, 0),
            sales_appointment_spacing_mins=30,
            max_advance_booking_days=30, # Max 30 days in advance
            min_advance_booking_hours=24 # Min 24 hours notice
        )

    def test_valid_date(self):
        # Test a date that should be valid (e.g., 2 days from now, Monday)
        # Adjusting test date dynamically for reliable testing regardless of current day
        today = date.today()
        # Find next valid weekday (e.g., Monday or Tuesday if current day is weekend/Monday)
        days_to_add = 0
        test_date = today + timedelta(days=days_to_add)
        while test_date.weekday() not in [0, 1, 2, 3, 4] or (test_date == today and datetime.now().hour + 24 >= 24):
            days_to_add += 1
            test_date = today + timedelta(days=days_to_add)
        
        # Ensure it's at least min_advance_booking_hours in future
        if datetime.combine(test_date, time(0,0)) <= datetime.now() + timedelta(hours=self.inventory_settings.min_advance_booking_hours):
            test_date += timedelta(days=1)
            while test_date.weekday() not in [0, 1, 2, 3, 4]: # Keep pushing if it becomes a weekend
                 test_date += timedelta(days=1)

        errors = validate_appointment_date(test_date, self.inventory_settings)
        self.assertEqual(errors, [])

    def test_date_too_far_in_future(self):
        # Test a date beyond max_advance_booking_days
        far_future_date = date.today() + timedelta(days=self.inventory_settings.max_advance_booking_days + 1)
        errors = validate_appointment_date(far_future_date, self.inventory_settings)
        self.assertIn(
            f"Appointments cannot be booked more than {self.inventory_settings.max_advance_booking_days} days in advance (up to {(date.today() + timedelta(days=self.inventory_settings.max_advance_booking_days)).strftime('%Y-%m-%d')}).",
            errors
        )
        self.assertEqual(len(errors), 1)

    def test_date_too_soon(self):
        # Test a date that is too soon (within min_advance_booking_hours)
        min_advance_hours = self.inventory_settings.min_advance_booking_hours
        
        # Calculate the earliest allowed datetime and corresponding date
        earliest_allowed_datetime = datetime.now() + timedelta(hours=min_advance_hours)
        earliest_allowed_date = earliest_allowed_datetime.date()

        # Test a date just before the earliest allowed date
        if earliest_allowed_date > date.today(): # Ensure we're not going into the past
            too_soon_date = earliest_allowed_date - timedelta(days=1)
        else: # If earliest allowed date is today, then today itself might be too soon based on time
            too_soon_date = date.today()

        errors = validate_appointment_date(too_soon_date, self.inventory_settings)
        self.assertIn(
            f"Appointments must be booked at least {min_advance_hours} hours in advance from now, meaning from {earliest_allowed_date.strftime('%Y-%m-%d')}.",
            errors
        )
        self.assertEqual(len(errors), 1)

    def test_date_on_closed_day(self):
        # Test a weekend date (Saturday or Sunday) if open days are Mon-Fri
        today = date.today()
        closed_date = today + timedelta(days=1) # Start checking tomorrow
        while closed_date.weekday() not in [5, 6]: # 5=Saturday, 6=Sunday
            closed_date += timedelta(days=1)

        errors = validate_appointment_date(closed_date, self.inventory_settings)
        self.assertIn("Appointments are not available on the selected day of the week.", errors)
        self.assertEqual(len(errors), 1)

    def test_no_inventory_settings(self):
        # Test with no inventory settings provided (should return no errors)
        test_date = date.today() + timedelta(days=7)
        errors = validate_appointment_date(test_date, None)
        self.assertEqual(errors, [])

    def test_inventory_settings_different_open_days(self):
        # Test with different open days (e.g., only weekends)
        settings_weekends = InventorySettingsFactory(
            sales_booking_open_days="Sat,Sun",
            pk=99 # Ensure unique PK for factory
        )
        
        today = date.today()
        
        # Test a weekday (should be invalid)
        weekday_date = today + timedelta(days=1)
        while weekday_date.weekday() in [5, 6]: # Ensure it's a weekday
            weekday_date += timedelta(days=1)
        
        errors = validate_appointment_date(weekday_date, settings_weekends)
        self.assertIn("Appointments are not available on the selected day of the week.", errors)

        # Test a weekend (should be valid)
        weekend_date = today + timedelta(days=1)
        while weekend_date.weekday() not in [5, 6]: # Ensure it's a weekend
            weekend_date += timedelta(days=1)
        
        # Ensure it's also not too soon
        earliest_allowed_datetime = datetime.now() + timedelta(hours=settings_weekends.min_advance_booking_hours)
        earliest_allowed_date = earliest_allowed_datetime.date()
        if weekend_date < earliest_allowed_date:
            weekend_date = earliest_allowed_date
            while weekend_date.weekday() not in [5, 6]:
                weekend_date += timedelta(days=1)


        errors = validate_appointment_date(weekend_date, settings_weekends)
        self.assertEqual(errors, [])
