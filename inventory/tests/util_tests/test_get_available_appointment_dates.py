# inventory/tests/utils/test_get_available_appointment_dates.py

from django.test import TestCase
from datetime import date, datetime, time, timedelta

from inventory.utils.get_sales_appointment_date_info import get_available_appointment_dates
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
        earliest_allowed_datetime = datetime.now() + timedelta(hours=settings.min_advance_booking_hours)
        earliest_allowed_date = earliest_allowed_datetime.date()

        self.assertNotIn(today, available_dates)
        if (today + timedelta(days=1)) < earliest_allowed_date:
            self.assertNotIn(today + timedelta(days=1), available_dates)
        
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
        
        for d in available_dates:
            self.assertLessEqual(d, date.today() + timedelta(days=3))
        
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

        for d in available_dates:
            self.assertNotIn(d.weekday(), [5, 6]) # 5=Saturday, 6=Sunday


    def test_excludes_single_blocked_date(self):
        # Create a specific settings for this test to control min_advance_booking_hours
        settings_for_block = InventorySettingsFactory(
            sales_booking_open_days="Mon,Tue,Wed,Thu,Fri,Sat,Sun", # All days open
            min_advance_booking_hours=0, # No advance notice required
            max_advance_booking_days=30,
            pk=104
        )
        
        # Block a specific date
        blocked_date = date.today() + timedelta(days=7) # Block a date 7 days from now
        BlockedSalesDateFactory(start_date=blocked_date, end_date=blocked_date)
        
        available_dates = get_available_appointment_dates(settings_for_block)
        self.assertNotIn(blocked_date, available_dates)

        # Check a date just before and after the blocked date is still available
        # if they also pass all other validations.
        self.assertIn(blocked_date - timedelta(days=1), available_dates)
        self.assertIn(blocked_date + timedelta(days=1), available_dates)


    def test_excludes_range_of_blocked_dates(self):
        # Create a specific settings for this test to control min_advance_booking_hours
        settings_for_block_range = InventorySettingsFactory(
            sales_booking_open_days="Mon,Tue,Wed,Thu,Fri,Sat,Sun", # All days open
            min_advance_booking_hours=0, # No advance notice required
            max_advance_booking_days=30,
            pk=105
        )

        # Block a range of dates
        start_block = date.today() + timedelta(days=10)
        end_block = date.today() + timedelta(days=12) # Block 3 days
        BlockedSalesDateFactory(start_date=start_block, end_date=end_block)

        available_dates = get_available_appointment_dates(settings_for_block_range)

        for i in range((end_block - start_block).days + 1):
            blocked_date = start_block + timedelta(days=i)
            self.assertNotIn(blocked_date, available_dates)
        
        # Check dates just outside the blocked range are still there (if they meet other criteria)
        # Ensure these boundary dates are also "open days" and not "too soon" relative to setup.
        # Given min_advance_booking_hours=0 and all days open, these should be present.
        self.assertIn(start_block - timedelta(days=1), available_dates)
        self.assertIn(end_block + timedelta(days=1), available_dates)


    def test_blocked_date_description_does_not_affect_exclusion(self):
        # Create a specific settings for this test
        settings_for_desc = InventorySettingsFactory(
            sales_booking_open_days="Mon,Tue,Wed,Thu,Fri,Sat,Sun", # All days open
            min_advance_booking_hours=0, # No advance notice required
            max_advance_booking_days=30,
            pk=106
        )

        blocked_date = date.today() + timedelta(days=5)
        BlockedSalesDateFactory(start_date=blocked_date, end_date=blocked_date, description="Public Holiday")

        available_dates = get_available_appointment_dates(settings_for_desc)
        self.assertNotIn(blocked_date, available_dates)
