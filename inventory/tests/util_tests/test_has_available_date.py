import datetime
from unittest.mock import patch
from django.test import TestCase
from django.utils import timezone
from inventory.models import BlockedSalesDate
from inventory.utils.has_available_date import has_available_date
from ..test_helpers.model_factories import InventorySettingsFactory, BlockedSalesDateFactory

class CheckHasAvailableDateTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.inventory_settings = InventorySettingsFactory(
            sales_booking_open_days="Mon,Tue,Wed,Thu,Fri",
            min_advance_booking_hours=24,
            max_advance_booking_days=30,
            deposit_lifespan_days=7,
        )

    def tearDown(self):
        BlockedSalesDate.objects.all().delete()

    def test_no_inventory_settings(self):
        self.assertFalse(has_available_date(None))

    @patch('django.utils.timezone.now')
    def test_dates_are_available_standard_case(self, mock_now):
        mock_now.return_value = timezone.make_aware(datetime.datetime(2025, 7, 7, 10, 0))
        self.assertTrue(has_available_date(self.inventory_settings))

    @patch('django.utils.timezone.now')
    def test_no_dates_available_all_days_blocked(self, mock_now):
        mock_now.return_value = timezone.make_aware(datetime.datetime(2025, 7, 7, 10, 0))
        BlockedSalesDateFactory(
            start_date=mock_now.return_value.date(),
            end_date=mock_now.return_value.date() + datetime.timedelta(days=31)
        )
        self.assertFalse(has_available_date(self.inventory_settings))

    @patch('django.utils.timezone.now')
    def test_no_dates_available_due_to_closed_days(self, mock_now):
        mock_now.return_value = timezone.make_aware(datetime.datetime(2025, 7, 4, 10, 0))
        self.inventory_settings.sales_booking_open_days = "Sun"
        self.inventory_settings.max_advance_booking_days = 1
        self.inventory_settings.save()
        self.assertFalse(has_available_date(self.inventory_settings))

    @patch('django.utils.timezone.now')
    def test_one_day_available(self, mock_now):
        mock_now.return_value = timezone.make_aware(datetime.datetime(2025, 7, 7, 10, 0))
        min_date = (mock_now.return_value + datetime.timedelta(hours=24)).date()
        max_date = mock_now.return_value.date() + datetime.timedelta(days=30)
        
        available_date = datetime.date(2025, 7, 15)

        BlockedSalesDateFactory(start_date=min_date, end_date=available_date - datetime.timedelta(days=1))
        BlockedSalesDateFactory(start_date=available_date + datetime.timedelta(days=1), end_date=max_date)

        self.assertTrue(has_available_date(self.inventory_settings))

    @patch('django.utils.timezone.now')
    def test_deposit_flow_has_available_date(self, mock_now):
        mock_now.return_value = timezone.make_aware(datetime.datetime(2025, 7, 7, 10, 0))
        self.assertTrue(has_available_date(self.inventory_settings, is_deposit_flow=True))

    @patch('django.utils.timezone.now')
    def test_deposit_flow_has_no_available_date(self, mock_now):
        mock_now.return_value = timezone.make_aware(datetime.datetime(2025, 7, 7, 10, 0))
        BlockedSalesDateFactory(
            start_date=mock_now.return_value.date(),
            end_date=mock_now.return_value.date() + datetime.timedelta(days=8)
        )
        self.assertFalse(has_available_date(self.inventory_settings, is_deposit_flow=True))
        
    @patch('django.utils.timezone.now')
    def test_no_dates_available_when_range_is_invalid(self, mock_now):
        mock_now.return_value = timezone.make_aware(datetime.datetime(2025, 7, 7, 10, 0))
        self.inventory_settings.min_advance_booking_hours = 72
        self.inventory_settings.max_advance_booking_days = 1
        self.inventory_settings.sales_booking_open_days = "Mon,Wed,Fri"
        self.inventory_settings.save()

        self.assertFalse(has_available_date(self.inventory_settings))
