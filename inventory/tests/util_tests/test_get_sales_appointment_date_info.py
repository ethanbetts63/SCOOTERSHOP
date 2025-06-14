# inventory/tests/test_utils/test_get_sales_appointment_date_info.py

import datetime
from django.test import TestCase
from inventory.models import InventorySettings, BlockedSalesDate
from inventory.utils.get_sales_appointment_date_info import get_sales_appointment_date_info
from ..test_helpers.model_factories import InventorySettingsFactory, BlockedSalesDateFactory

class GetSalesAppointmentDateInfoTest(TestCase):
    """
    Tests for the `get_sales_appointment_date_info` utility function.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up common data for all tests in this class.
        """
        # Ensure a fresh InventorySettings is created for each test run if not present
        cls.default_inventory_settings = InventorySettingsFactory(
            sales_appointment_start_time=datetime.time(9, 0),
            sales_appointment_end_time=datetime.time(17, 0),
            sales_appointment_spacing_mins=30,
            min_advance_booking_hours=24,  # Default: 24 hours notice
            max_advance_booking_days=90,   # Default: 90 days max booking
            deposit_lifespan_days=5,       # Default: 5 days for deposit flow
            sales_booking_open_days="Mon,Tue,Wed,Thu,Fri", # Default: Weekdays only
        )

    def tearDown(self):
        """
        Clean up after each test to ensure fresh settings for the next.
        """
        # Ensure default settings are reset if modified by a test
        self.default_inventory_settings.refresh_from_db()
        self.default_inventory_settings.sales_appointment_start_time = datetime.time(9, 0)
        self.default_inventory_settings.sales_appointment_end_time = datetime.time(17, 0)
        self.default_inventory_settings.sales_appointment_spacing_mins = 30
        self.default_inventory_settings.min_advance_booking_hours = 24
        self.default_inventory_settings.max_advance_booking_days = 90
        self.default_inventory_settings.deposit_lifespan_days = 5
        self.default_inventory_settings.sales_booking_open_days = "Mon,Tue,Wed,Thu,Fri"
        self.default_inventory_settings.save()
        BlockedSalesDate.objects.all().delete() # Clear any blocked dates created during tests


    def test_default_behavior(self):
        """
        Test that default min_date, max_date, and blocked_dates are correct
        with default InventorySettings and no BlockedSalesDate entries.
        """
        # Simulate current time for predictable min_date calculation
        # To avoid actual time affecting the test, we'll fix 'now' relative to today.
        # This is primarily for min_date, others are relative to date.today()
        
        # Adjust min_advance_booking_hours to make today a valid start for testing
        self.default_inventory_settings.min_advance_booking_hours = 0
        self.default_inventory_settings.save()

        min_date, max_date, blocked_dates = get_sales_appointment_date_info(self.default_inventory_settings)

        today = datetime.date.today()
        # Min date should be today if min_advance_booking_hours is 0
        self.assertEqual(min_date, today)
        # Max date should be today + 90 days by default
        self.assertEqual(max_date, today + datetime.timedelta(days=90))

        # Check for blocked weekends within the range (Sat, Sun for "Mon,Tue,Wed,Thu,Fri")
        expected_blocked_dates = []
        current_day = today
        while current_day <= max_date:
            if current_day.weekday() >= 5: # Saturday (5) or Sunday (6)
                expected_blocked_dates.append(current_day.strftime('%Y-%m-%d'))
            current_day += datetime.timedelta(days=1)
        
        self.assertEqual(blocked_dates, sorted(list(set(expected_blocked_dates))))

    def test_no_inventory_settings_provided(self):
        """
        Test that the function returns default values if no InventorySettings are provided.
        """
        # Delete existing settings to simulate no settings in DB
        InventorySettings.objects.all().delete()
        min_date, max_date, blocked_dates = get_sales_appointment_date_info(None) # Pass None

        today = datetime.date.today()
        self.assertEqual(min_date, today)
        self.assertEqual(max_date, today + datetime.timedelta(days=90))
        self.assertEqual(blocked_dates, [])
        # Recreate for other tests
        self.default_inventory_settings = InventorySettingsFactory()


    def test_min_advance_booking_hours(self):
        """
        Test that min_date is correctly shifted based on min_advance_booking_hours.
        """
        # Set min_advance_booking_hours to make tomorrow the earliest
        self.default_inventory_settings.min_advance_booking_hours = 24
        self.default_inventory_settings.save()

        min_date, _, _ = get_sales_appointment_date_info(self.default_inventory_settings)
        expected_min_date = datetime.date.today() + datetime.timedelta(days=1) # Tomorrow
        self.assertEqual(min_date, expected_min_date)

        # Set min_advance_booking_hours to make day after tomorrow the earliest (e.g., 48.1 hours)
        self.default_inventory_settings.min_advance_booking_hours = 48
        self.default_inventory_settings.save()
        min_date, _, _ = get_sales_appointment_date_info(self.default_inventory_settings)
        expected_min_date = datetime.date.today() + datetime.timedelta(days=2) # Day after tomorrow
        self.assertEqual(min_date, expected_min_date)

    def test_max_advance_booking_days(self):
        """
        Test that max_date is correctly shifted based on max_advance_booking_days.
        """
        self.default_inventory_settings.max_advance_booking_days = 30
        self.default_inventory_settings.save()

        _, max_date, _ = get_sales_appointment_date_info(self.default_inventory_settings)
        expected_max_date = datetime.date.today() + datetime.timedelta(days=30)
        self.assertEqual(max_date, expected_max_date)

    def test_deposit_flow_caps_max_date(self):
        """
        Test that max_date is capped by deposit_lifespan_days when is_deposit_flow is True.
        """
        self.default_inventory_settings.max_advance_booking_days = 90
        self.default_inventory_settings.deposit_lifespan_days = 10 # Shorter lifespan
        self.default_inventory_settings.min_advance_booking_hours = 0 # To ensure min_date doesn't interfere
        self.default_inventory_settings.save()

        # is_deposit_flow = True, so deposit_expiry_date (today + 10 days) should be the max_date
        min_date, max_date, _ = get_sales_appointment_date_info(self.default_inventory_settings, is_deposit_flow=True)
        expected_max_date = datetime.date.today() + datetime.timedelta(days=10)
        self.assertEqual(max_date, expected_max_date)
        self.assertEqual(min_date, datetime.date.today()) # Still today

        # Test case where general_max_date is shorter than deposit_expiry_date
        self.default_inventory_settings.max_advance_booking_days = 5
        self.default_inventory_settings.deposit_lifespan_days = 10 # Longer lifespan
        self.default_inventory_settings.save()

        min_date, max_date, _ = get_sales_appointment_date_info(self.default_inventory_settings, is_deposit_flow=True)
        expected_max_date = datetime.date.today() + datetime.timedelta(days=5) # General max should apply
        self.assertEqual(max_date, expected_max_date)

    def test_blocked_sales_dates(self):
        """
        Test that dates explicitly blocked by BlockedSalesDate are included in blocked_dates.
        """
        today = datetime.date.today()
        # Block a range of dates
        BlockedSalesDateFactory(
            start_date=today + datetime.timedelta(days=5),
            end_date=today + datetime.timedelta(days=7),
            description="Test Block"
        )
        # Block a single date
        BlockedSalesDateFactory(
            start_date=today + datetime.timedelta(days=10),
            end_date=today + datetime.timedelta(days=10),
            description="Single Day Block"
        )

        self.default_inventory_settings.min_advance_booking_hours = 0
        self.default_inventory_settings.sales_booking_open_days = "Mon,Tue,Wed,Thu,Fri,Sat,Sun" # All days open to isolate BlockedSalesDate
        self.default_inventory_settings.save()

        min_date, max_date, blocked_dates = get_sales_appointment_date_info(self.default_inventory_settings)

        expected_blocked_dates = []
        for i in range(5, 8): # Days 5, 6, 7
            expected_blocked_dates.append((today + datetime.timedelta(days=i)).strftime('%Y-%m-%d'))
        expected_blocked_dates.append((today + datetime.timedelta(days=10)).strftime('%Y-%m-%d'))

        self.assertIn((today + datetime.timedelta(days=5)).strftime('%Y-%m-%d'), blocked_dates)
        self.assertIn((today + datetime.timedelta(days=6)).strftime('%Y-%m-%d'), blocked_dates)
        self.assertIn((today + datetime.timedelta(days=7)).strftime('%Y-%m-%d'), blocked_dates)
        self.assertIn((today + datetime.timedelta(days=10)).strftime('%Y-%m-%d'), blocked_dates)
        # Check that no other dates are blocked if all days are open
        for i in range(max(0, self.default_inventory_settings.min_advance_booking_hours // 24), 15):
            d = today + datetime.timedelta(days=i)
            d_str = d.strftime('%Y-%m-%d')
            if d_str not in expected_blocked_dates:
                self.assertNotIn(d_str, blocked_dates)
        
        # Ensure no duplicates and sorted
        self.assertEqual(blocked_dates, sorted(list(set(blocked_dates))))


    def test_sales_booking_open_days(self):
        """
        Test that days not in sales_booking_open_days are correctly blocked.
        """
        today = datetime.date.today()
        # Set only Monday and Tuesday as open days
        self.default_inventory_settings.sales_booking_open_days = "Mon,Tue"
        self.default_inventory_settings.min_advance_booking_hours = 0
        self.default_inventory_settings.max_advance_booking_days = 7 # Limit range for easier testing
        self.default_inventory_settings.save()

        min_date, max_date, blocked_dates = get_sales_appointment_date_info(self.default_inventory_settings)

        expected_blocked_dates = []
        current_day = min_date
        while current_day <= max_date:
            # Monday (0), Tuesday (1) are allowed. Others should be blocked.
            if current_day.weekday() not in [0, 1]:
                expected_blocked_dates.append(current_day.strftime('%Y-%m-%d'))
            current_day += datetime.timedelta(days=1)
        
        self.assertEqual(blocked_dates, sorted(list(set(expected_blocked_dates))))

    def test_max_date_capped_by_min_date(self):
        """
        Test that max_date is capped to min_date if settings make it earlier.
        This can happen if min_advance_booking_hours pushes min_date far out,
        and max_advance_booking_days or deposit_lifespan_days is very small.
        """
        # Set very high min_advance_booking_hours
        self.default_inventory_settings.min_advance_booking_hours = 720 # 30 days
        # Set very low max_advance_booking_days
        self.default_inventory_settings.max_advance_booking_days = 1
        self.default_inventory_settings.save()

        min_date, max_date, _ = get_sales_appointment_date_info(self.default_inventory_settings)

        expected_min_date = datetime.date.today() + datetime.timedelta(days=30)
        self.assertEqual(min_date, expected_min_date)
        # Max date should be capped to min_date
        self.assertEqual(max_date, expected_min_date)

    def test_combined_blocking_factors(self):
        """
        Test that all blocking factors (min_advance, max_advance, blocked dates, open days)
        work together correctly.
        """
        today = datetime.date.today()

        # Custom settings
        self.default_inventory_settings.min_advance_booking_hours = 24 # Tomorrow is earliest
        self.default_inventory_settings.max_advance_booking_days = 14 # Two weeks max
        self.default_inventory_settings.sales_booking_open_days = "Mon,Wed,Fri" # Only M, W, F
        self.default_inventory_settings.save()

        # Block a specific date within the range
        blocked_date_in_range = today + datetime.timedelta(days=5) # Example: next Tuesday/Wednesday
        BlockedSalesDateFactory(
            start_date=blocked_date_in_range,
            end_date=blocked_date_in_range,
            description="Specific blocked day"
        )
        
        min_date, max_date, blocked_dates = get_sales_appointment_date_info(self.default_inventory_settings)

        expected_min_date = today + datetime.timedelta(days=1)
        expected_max_date = today + datetime.timedelta(days=14)

        self.assertEqual(min_date, expected_min_date)
        self.assertEqual(max_date, expected_max_date)

        calculated_blocked_dates = []
        current_day = min_date
        while current_day <= max_date:
            # Check for non-open days (weekdays 0-6: Mon,Tue,Wed,Thu,Fri,Sat,Sun)
            # Allowed are Mon(0), Wed(2), Fri(4)
            if current_day.weekday() not in [0, 2, 4]:
                calculated_blocked_dates.append(current_day.strftime('%Y-%m-%d'))
            
            # Check for explicitly blocked date
            if current_day == blocked_date_in_range:
                calculated_blocked_dates.append(current_day.strftime('%Y-%m-%d'))

            current_day += datetime.timedelta(days=1)
        
        # Ensure the final blocked_dates list matches the calculated one
        self.assertEqual(blocked_dates, sorted(list(set(calculated_blocked_dates))))

