import datetime
from unittest.mock import patch
from django.test import TestCase
from django.utils import timezone
from inventory.models import BlockedSalesDate
from inventory.utils.get_sales_appointment_date_info import get_sales_appointment_date_info

from inventory.tests.test_helpers.model_factories import InventorySettingsFactory, BlockedSalesDateFactory

class GetSalesAppointmentDateInfoTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        """Set up a default InventorySettings instance for all tests."""
        cls.default_inventory_settings = InventorySettingsFactory(
            sales_appointment_start_time=datetime.time(9, 0),
            sales_appointment_end_time=datetime.time(17, 0),
            sales_appointment_spacing_mins=30,
            min_advance_booking_hours=24,
            max_advance_booking_days=90,
            deposit_lifespan_days=5,
            sales_booking_open_days="Mon,Tue,Wed,Thu,Fri",
        )

    def tearDown(self):
        """Clean up BlockedSalesDate objects after each test."""
        BlockedSalesDate.objects.all().delete()

    @patch('django.utils.timezone.now')
    def test_default_behavior(self, mock_now):
        """Test default date calculations with no advance booking hours."""
        mock_now.return_value = timezone.make_aware(datetime.datetime(2025, 7, 1, 10, 0))
        today = mock_now.return_value.date()

        self.default_inventory_settings.min_advance_booking_hours = 0
        self.default_inventory_settings.save()

        min_date, max_date, blocked_dates = get_sales_appointment_date_info(self.default_inventory_settings)

        self.assertEqual(min_date, today)
        self.assertEqual(max_date, today + datetime.timedelta(days=90))

        # Check that weekends are correctly blocked
        expected_blocked = []
        current_day = today
        while current_day <= max_date:
            if current_day.weekday() >= 5: # Saturday or Sunday
                expected_blocked.append(current_day.strftime("%Y-%m-%d"))
            current_day += datetime.timedelta(days=1)
        
        self.assertEqual(blocked_dates, sorted(list(set(expected_blocked))))

    def test_no_inventory_settings_provided(self):
        """Test fallback behavior when no inventory settings are provided."""
        min_date, max_date, blocked_dates = get_sales_appointment_date_info(None)
        today = timezone.localdate()
        self.assertEqual(min_date, today)
        self.assertEqual(max_date, today + datetime.timedelta(days=90))
        self.assertEqual(blocked_dates, [])

    @patch('django.utils.timezone.now')
    def test_min_advance_booking_hours_pushes_min_date(self, mock_now):
        """Test that min_advance_booking_hours correctly pushes the min_date."""
        mock_now.return_value = timezone.make_aware(datetime.datetime(2025, 7, 1, 10, 0))
        
        # 24 hours advance should push min_date to tomorrow
        self.default_inventory_settings.min_advance_booking_hours = 24
        self.default_inventory_settings.save()
        min_date, _, _ = get_sales_appointment_date_info(self.default_inventory_settings)
        expected_min_date = mock_now.return_value.date() + datetime.timedelta(days=1)
        self.assertEqual(min_date, expected_min_date)

        # 48 hours advance should push min_date two days forward
        self.default_inventory_settings.min_advance_booking_hours = 48
        self.default_inventory_settings.save()
        min_date, _, _ = get_sales_appointment_date_info(self.default_inventory_settings)
        expected_min_date = mock_now.return_value.date() + datetime.timedelta(days=2)
        self.assertEqual(min_date, expected_min_date)

    @patch('django.utils.timezone.now')
    def test_min_date_pushed_if_all_slots_unavailable(self, mock_now):
        """Test that min_date is advanced if all of today's slots are in the past."""
        # Set current time to 18:00, after all appointments (which end at 17:00)
        mock_now.return_value = timezone.make_aware(datetime.datetime(2025, 7, 1, 18, 0))
        
        # With 24h advance notice, today (Jul 1) would normally be blocked.
        # The earliest booking is Jul 2, 18:00.
        # Since all slots on Jul 2 are before 18:00, the whole day should be unavailable.
        # The first available date should be Jul 3.
        self.default_inventory_settings.min_advance_booking_hours = 24
        self.default_inventory_settings.save()

        min_date, _, _ = get_sales_appointment_date_info(self.default_inventory_settings)
        
        # Earliest allowed datetime is 2025-07-02 18:00.
        # End time on 2025-07-02 is 17:00, which is before the earliest allowed time.
        # Therefore, min_date should be pushed to 2025-07-03.
        expected_min_date = timezone.make_aware(datetime.datetime(2025, 7, 3)).date()
        self.assertEqual(min_date, expected_min_date)

    @patch('django.utils.timezone.now')
    def test_max_advance_booking_days(self, mock_now):
        """Test that max_advance_booking_days correctly sets the max_date."""
        mock_now.return_value = timezone.make_aware(datetime.datetime(2025, 7, 1, 10, 0))
        today = mock_now.return_value.date()

        self.default_inventory_settings.max_advance_booking_days = 30
        self.default_inventory_settings.save()

        _, max_date, _ = get_sales_appointment_date_info(self.default_inventory_settings)
        expected_max_date = today + datetime.timedelta(days=30)
        self.assertEqual(max_date, expected_max_date)

    @patch('django.utils.timezone.now')
    def test_deposit_flow_caps_max_date(self, mock_now):
        """Test that the deposit flow correctly caps the max_date by deposit_lifespan_days."""
        mock_now.return_value = timezone.make_aware(datetime.datetime(2025, 7, 1, 10, 0))
        today = mock_now.return_value.date()

        self.default_inventory_settings.max_advance_booking_days = 90
        self.default_inventory_settings.deposit_lifespan_days = 10
        self.default_inventory_settings.min_advance_booking_hours = 0
        self.default_inventory_settings.save()

        _, max_date, _ = get_sales_appointment_date_info(self.default_inventory_settings, is_deposit_flow=True)
        expected_max_date = today + datetime.timedelta(days=10)
        self.assertEqual(max_date, expected_max_date)

        # Test when max_advance_booking_days is shorter than deposit_lifespan_days
        self.default_inventory_settings.max_advance_booking_days = 5
        self.default_inventory_settings.save()
        _, max_date, _ = get_sales_appointment_date_info(self.default_inventory_settings, is_deposit_flow=True)
        expected_max_date = today + datetime.timedelta(days=5)
        self.assertEqual(max_date, expected_max_date)

    @patch('django.utils.timezone.now')
    def test_blocked_sales_dates(self, mock_now):
        """Test that manually blocked dates are correctly identified."""
        mock_now.return_value = timezone.make_aware(datetime.datetime(2025, 7, 1, 10, 0))
        today = mock_now.return_value.date()

        BlockedSalesDateFactory(start_date=today + datetime.timedelta(days=5), end_date=today + datetime.timedelta(days=7))
        BlockedSalesDateFactory(start_date=today + datetime.timedelta(days=10), end_date=today + datetime.timedelta(days=10))

        self.default_inventory_settings.min_advance_booking_hours = 0
        self.default_inventory_settings.sales_booking_open_days = "Mon,Tue,Wed,Thu,Fri,Sat,Sun"
        self.default_inventory_settings.save()

        _, _, blocked_dates = get_sales_appointment_date_info(self.default_inventory_settings)

        expected_blocked = [
            (today + datetime.timedelta(days=5)).strftime("%Y-%m-%d"),
            (today + datetime.timedelta(days=6)).strftime("%Y-%m-%d"),
            (today + datetime.timedelta(days=7)).strftime("%Y-%m-%d"),
            (today + datetime.timedelta(days=10)).strftime("%Y-%m-%d"),
        ]
        self.assertEqual(blocked_dates, sorted(list(set(expected_blocked))))

    @patch('django.utils.timezone.now')
    def test_sales_booking_open_days(self, mock_now):
        """Test that closed days are correctly added to the blocked dates list."""
        mock_now.return_value = timezone.make_aware(datetime.datetime(2025, 7, 1, 10, 0)) # A Tuesday
        today = mock_now.return_value.date()

        self.default_inventory_settings.sales_booking_open_days = "Wed,Fri" # Block Mon, Tue, Thu, Sat, Sun
        self.default_inventory_settings.min_advance_booking_hours = 0
        self.default_inventory_settings.max_advance_booking_days = 6 # Up to next Monday
        self.default_inventory_settings.save()

        min_date, max_date, blocked_dates = get_sales_appointment_date_info(self.default_inventory_settings)

        expected_blocked = []
        current_day = min_date
        while current_day <= max_date:
            if current_day.weekday() not in [2, 4]: # Not a Wednesday or Friday
                expected_blocked.append(current_day.strftime("%Y-%m-%d"))
            current_day += datetime.timedelta(days=1)

        self.assertEqual(blocked_dates, sorted(list(set(expected_blocked))))

    @patch('django.utils.timezone.now')
    def test_max_date_capped_by_min_date(self, mock_now):
        """Test that max_date cannot be earlier than min_date."""
        mock_now.return_value = timezone.make_aware(datetime.datetime(2025, 7, 1, 10, 0))
        
        # Set min advance booking to 30 days, but max booking to only 1 day
        self.default_inventory_settings.min_advance_booking_hours = 24 * 30 # 720 hours
        self.default_inventory_settings.max_advance_booking_days = 1
        self.default_inventory_settings.save()

        min_date, max_date, _ = get_sales_appointment_date_info(self.default_inventory_settings)

        expected_min_date = mock_now.return_value.date() + datetime.timedelta(days=30)
        self.assertEqual(min_date, expected_min_date)
        self.assertEqual(max_date, expected_min_date) # max_date should be pushed to equal min_date

