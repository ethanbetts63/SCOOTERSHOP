# inventory/tests/utils/test_get_available_appointment_dates.py

from django.test import TestCase
from datetime import date, datetime, time, timedelta

from inventory.utils.get_available_appointment_dates import get_available_appointment_dates
from inventory.models import InventorySettings, BlockedSalesDate
from ..test_helpers.model_factories import InventorySettingsFactory, BlockedSalesDateFactory

class GetAvailableAppointmentDatesUtilTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Create a default InventorySettings instance for testing
        cls.inventory_settings_default = InventorySettingsFactory(
            sales_booking_open_days="Mon,Tue,Wed,Thu,Fri", # Weekdays only
            min_advance_booking_hours=24, # 24 hours notice
            max_advance_booking_days=30 # Max 30 days into future
        )

    def test_no_inventory_settings(self):
        # Should return an empty list if no inventory settings are provided
        available_dates = get_available_appointment_dates(None)
        self.assertEqual(available_dates, [])

    def test_default_settings_valid_dates(self):
        # Test that dates within the valid range and on open days are returned
        today = date.today()
        expected_dates = []
        earliest_allowed_datetime = datetime.now() + timedelta(hours=self.inventory_settings_default.min_advance_booking_hours)
        earliest_allowed_date = earliest_allowed_datetime.date()

        for i in range(self.inventory_settings_default.max_advance_booking_days + 1):
            current_date = today + timedelta(days=i)
            # Simulate the internal logic of validate_appointment_date and get_available_appointment_dates
            # This is essentially re-checking the conditions for what 'should' be valid
            if (current_date.weekday() in [0, 1, 2, 3, 4] and # Mon-Fri
                current_date >= earliest_allowed_date and
                current_date <= today + timedelta(days=self.inventory_settings_default.max_advance_booking_days)):
                expected_dates.append(current_date)
        
        available_dates = get_available_appointment_dates(self.inventory_settings_default)
        self.assertEqual(available_dates, expected_dates)


    def test_excludes_dates_too_soon(self):
        # Set min_advance_booking_hours to make today and maybe tomorrow too soon
        settings = InventorySettingsFactory(
            sales_booking_open_days="Mon,Tue,Wed,Thu,Fri,Sat,Sun", # All days open
            min_advance_booking_hours=48, # 48 hours notice (2 full days)
            max_advance_booking_days=30,
            pk=101
        )
        
        available_dates = get_available_appointment_dates(settings)
        
        today = date.today()
        # Earliest allowed date will be at least 2 days from now
        earliest_allowed_datetime = datetime.now() + timedelta(hours=settings.min_advance_booking_hours)
        earliest_allowed_date = earliest_allowed_datetime.date()

        self.assertNotIn(today, available_dates)
        if (today + timedelta(days=1)) < earliest_allowed_date:
            self.assertNotIn(today + timedelta(days=1), available_dates)
        
        # Ensure the first date is indeed the earliest allowed date or later
        if available_dates:
            self.assertGreaterEqual(available_dates[0], earliest_allowed_date)

    def test_excludes_dates_too_far_in_future(self):
        # Set a small max_advance_booking_days
        settings = InventorySettingsFactory(
            sales_booking_open_days="Mon,Tue,Wed,Thu,Fri,Sat,Sun",
            min_advance_booking_hours=0, # No minimum notice
            max_advance_booking_days=3, # Only 3 days from today
            pk=102
        )
        available_dates = get_available_appointment_dates(settings)
        
        # All dates should be within today to today + 3 days
        for d in available_dates:
            self.assertLessEqual(d, date.today() + timedelta(days=3))
        
        # Check that a date beyond the limit is not included
        self.assertNotIn(date.today() + timedelta(days=4), available_dates)


    def test_excludes_closed_days(self):
        # Settings with only weekdays open
        settings = InventorySettingsFactory(
            sales_booking_open_days="Mon,Tue,Wed,Thu,Fri",
            min_advance_booking_hours=0, # No minimum notice
            max_advance_booking_days=14, # Check for a couple of weeks
            pk=103
        )
        available_dates = get_available_appointment_dates(settings)

        # Check that no Saturdays or Sundays are in the list
        for d in available_dates:
            self.assertNotIn(d.weekday(), [5, 6]) # 5=Saturday, 6=Sunday


    def test_excludes_single_blocked_date(self):
        # Block a specific date
        blocked_date = date.today() + timedelta(days=7) # Block a date 7 days from now
        BlockedSalesDateFactory(start_date=blocked_date, end_date=blocked_date)

        # Ensure that the blocked date would otherwise be valid
        # (e.g., it's an open day and within min/max advance)
        self.inventory_settings_default.min_advance_booking_hours = 0 # Temporarily bypass this check
        self.inventory_settings_default.save() # Save the change for this test's context
        
        available_dates = get_available_appointment_dates(self.inventory_settings_default)
        self.assertNotIn(blocked_date, available_dates)

        # Reset for other tests if needed (though new test DB for each run helps)
        # InventorySettings.objects.filter(pk=self.inventory_settings_default.pk).update(min_advance_booking_hours=24)


    def test_excludes_range_of_blocked_dates(self):
        # Block a range of dates
        start_block = date.today() + timedelta(days=10)
        end_block = date.today() + timedelta(days=12) # Block 3 days
        BlockedSalesDateFactory(start_date=start_block, end_date=end_block)

        # Temporarily bypass min_advance_booking_hours if it interferes
        self.inventory_settings_default.min_advance_booking_hours = 0
        self.inventory_settings_default.save()

        available_dates = get_available_appointment_dates(self.inventory_settings_default)

        for i in range((end_block - start_block).days + 1):
            blocked_date = start_block + timedelta(days=i)
            # Ensure these dates are not in the available list
            self.assertNotIn(blocked_date, available_dates)
        
        # Check dates just outside the blocked range are still there (if they meet other criteria)
        self.assertIn(start_block - timedelta(days=1), available_dates)
        self.assertIn(end_block + timedelta(days=1), available_dates)


    def test_blocked_date_description_does_not_affect_exclusion(self):
        # Ensure that description on BlockedSalesDate doesn't prevent exclusion
        blocked_date = date.today() + timedelta(days=5)
        BlockedSalesDateFactory(start_date=blocked_date, end_date=blocked_date, description="Public Holiday")

        self.inventory_settings_default.min_advance_booking_hours = 0
        self.inventory_settings_default.save()

        available_dates = get_available_appointment_dates(self.inventory_settings_default)
        self.assertNotIn(blocked_date, available_dates)
