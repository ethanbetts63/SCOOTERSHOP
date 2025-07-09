import datetime
from unittest.mock import patch
from django.test import TestCase
from django.utils import timezone
from inventory.models import BlockedSalesDate
from inventory.utils.has_available_date import (
    has_available_date_for_deposit_flow,
    has_available_date_for_viewing_flow,
)
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

    def test_flows_return_false_with_no_settings(self):
        self.assertFalse(has_available_date_for_deposit_flow(None))
        self.assertFalse(has_available_date_for_viewing_flow(None))

    @patch('django.utils.timezone.now')
    def test_viewing_flow_is_true_when_dates_available(self, mock_now):
        mock_now.return_value = timezone.make_aware(datetime.datetime(2025, 7, 7, 10, 0))
        self.assertTrue(has_available_date_for_viewing_flow(self.inventory_settings))

    @patch('django.utils.timezone.now')
    def test_viewing_flow_is_false_when_all_dates_blocked(self, mock_now):
        mock_now.return_value = timezone.make_aware(datetime.datetime(2025, 7, 7, 10, 0))
        BlockedSalesDateFactory(
            start_date=mock_now.return_value.date(),
            end_date=mock_now.return_value.date() + datetime.timedelta(days=31)
        )
        self.assertFalse(has_available_date_for_viewing_flow(self.inventory_settings))

    @patch('django.utils.timezone.now')
    def test_deposit_flow_is_true_when_dates_available(self, mock_now):
        mock_now.return_value = timezone.make_aware(datetime.datetime(2025, 7, 7, 10, 0))
        self.assertTrue(has_available_date_for_deposit_flow(self.inventory_settings))

    @patch('django.utils.timezone.now')
    def test_deposit_flow_is_false_when_dates_only_available_outside_lifespan(self, mock_now):
        mock_now.return_value = timezone.make_aware(datetime.datetime(2025, 7, 7, 10, 0))
        BlockedSalesDateFactory(
            start_date=mock_now.return_value.date(),
            end_date=mock_now.return_value.date() + datetime.timedelta(days=8)
        )
        self.assertTrue(has_available_date_for_viewing_flow(self.inventory_settings)) 
        self.assertFalse(has_available_date_for_deposit_flow(self.inventory_settings))

    @patch('django.utils.timezone.now')
    def test_flows_return_false_when_range_is_invalid(self, mock_now):
        mock_now.return_value = timezone.make_aware(datetime.datetime(2025, 7, 10, 10, 0))
        self.inventory_settings.min_advance_booking_hours = 72
        self.inventory_settings.max_advance_booking_days = 1 
        self.inventory_settings.sales_booking_open_days = "Mon,Tue,Wed,Thu,Fri"
        self.inventory_settings.save()

        self.assertFalse(has_available_date_for_viewing_flow(self.inventory_settings))
        self.assertFalse(has_available_date_for_deposit_flow(self.inventory_settings))
