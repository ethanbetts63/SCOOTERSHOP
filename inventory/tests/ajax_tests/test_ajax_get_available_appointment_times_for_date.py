# inventory/tests/ajax/test_get_available_appointment_times_for_date.py

from django.test import TestCase, Client
from django.urls import reverse
from unittest.mock import patch
from datetime import time, datetime
from django.utils import timezone
from ..test_helpers.model_factories import InventorySettingsFactory

AJAX_GET_TIMES_UTIL_PATH = 'inventory.ajax.ajax_get_available_appointment_times_for_date.get_available_appointment_times'

class GetAvailableAppointmentTimesForDateAjaxTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        cls.ajax_url = reverse('inventory:ajax_get_appointment_times')

        cls.default_inventory_settings = InventorySettingsFactory(
            sales_appointment_start_time=time(9, 0),
            sales_appointment_end_time=time(17, 0),
            sales_appointment_spacing_mins=30,
            min_advance_booking_hours=2,
            pk=1
        )

    def test_missing_date_parameter(self):
        response = self.client.get(self.ajax_url)
        self.assertEqual(response.status_code, 400)
        self.assertJSONEqual(response.content.decode(), {'error': 'Date parameter is missing.'})

    def test_invalid_date_format(self):
        response = self.client.get(self.ajax_url + '?date=2023/10/26')
        self.assertEqual(response.status_code, 400)
        self.assertJSONEqual(response.content.decode(), {'error': 'Invalid date format. Use YYYY-MM-DD.'})


    @patch('inventory.models.InventorySettings.objects.first')
    def test_no_inventory_settings(self, mock_settings_first):
        mock_settings_first.return_value = None
        response = self.client.get(self.ajax_url + '?date=2025-01-01')
        self.assertEqual(response.status_code, 500)
        self.assertJSONEqual(response.content.decode(), {'error': 'Inventory settings not found.'})

    @patch(AJAX_GET_TIMES_UTIL_PATH) # Corrected patch target
    @patch('inventory.models.InventorySettings.objects.first')
    def test_successful_response_future_date(self, mock_settings_first, mock_get_times_util):
        mock_settings_first.return_value = self.default_inventory_settings
        # The mock should return strings, and the AJAX view will format them into dictionaries
        mock_get_times_util.return_value = ["09:00", "09:30", "10:00"] 

        selected_date_str = "2025-07-01"
        response = self.client.get(self.ajax_url + f'?date={selected_date_str}')

        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content.decode(), {
            'available_times': [
                {"value": "09:00", "text": "09:00"},
                {"value": "09:30", "text": "09:30"},
                {"value": "10:00", "text": "10:00"}
            ]
        })
        # Assert that the mocked utility function was called with the correct arguments
        mock_get_times_util.assert_called_once_with(
            datetime.strptime(selected_date_str, '%Y-%m-%d').date(),
            self.default_inventory_settings
        )

    @patch(AJAX_GET_TIMES_UTIL_PATH) # Corrected patch target
    @patch('inventory.models.InventorySettings.objects.first')
    @patch('django.utils.timezone.now')
    def test_successful_response_today_date(self, mock_now, mock_settings_first, mock_get_times_util):
        # Fix the current time for predictable test results
        fixed_now = datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.get_current_timezone())
        mock_now.return_value = fixed_now

        mock_settings_first.return_value = self.default_inventory_settings

        # Mock the return value of get_available_appointment_times based on the test scenario.
        # This is the list of formatted time strings that the mocked utility function will return.
        mock_get_times_util.return_value = ["15:00", "15:30", "16:00", "16:30", "17:00"]
        
        today_str = timezone.localdate(fixed_now).strftime('%Y-%m-%d')
        response = self.client.get(self.ajax_url + f'?date={today_str}')

        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content.decode(), {
            'available_times': [
                {"value": "15:00", "text": "15:00"},
                {"value": "15:30", "text": "15:30"},
                {"value": "16:00", "text": "16:00"},
                {"value": "16:30", "text": "16:30"},
                {"value": "17:00", "text": "17:00"}
            ]
        })
        # Assert that the mocked utility function was called with the correct arguments
        mock_get_times_util.assert_called_once_with(
            timezone.localdate(fixed_now),
            self.default_inventory_settings
        )
    
    @patch(AJAX_GET_TIMES_UTIL_PATH) # Corrected patch target
    @patch('inventory.models.InventorySettings.objects.first')
    def test_no_available_times_for_date(self, mock_settings_first, mock_get_times_util):
        mock_settings_first.return_value = self.default_inventory_settings
        # The mock should return an empty list, and the AJAX view will format this.
        mock_get_times_util.return_value = [] 

        selected_date_str = "2025-07-04"
        response = self.client.get(self.ajax_url + f'?date={selected_date_str}')

        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content.decode(), {'available_times': []})
        # Assert that the mocked utility function was called with the correct arguments
        mock_get_times_util.assert_called_once_with(
            datetime.strptime(selected_date_str, '%Y-%m-%d').date(),
            self.default_inventory_settings
        )

