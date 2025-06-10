from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.http import JsonResponse
import datetime
import json
from unittest.mock import patch, Mock

# Corrected import path for the view function
from service.ajax.ajax_get_available_dropoff_times_for_date import get_available_dropoff_times_for_date

class AjaxGetAvailableTimesForDateTest(TestCase):
    """
    Tests for the AJAX view `get_available_dropoff_times_for_date`.
    This test suite focuses on the view's handling of requests and responses,
    mocking the `get_available_dropoff_times` utility function to isolate logic.
    """

    def setUp(self):
        """
        Set up for each test method.
        Initialize a RequestFactory to create dummy request objects.
        """
        self.factory = RequestFactory()

    # Corrected patch path: specify the module where get_available_dropoff_times is imported
    @patch('service.ajax.ajax_get_available_dropoff_times_for_date.get_available_dropoff_times')
    def test_missing_date_parameter(self, mock_get_available_dropoff_times):
        """
        Test that the view returns a 400 error if the 'date' parameter is missing.
        """
        request = self.factory.get('/ajax/available-times/') # No 'date' parameter
        response = get_available_dropoff_times_for_date(request)

        self.assertEqual(response.status_code, 400)
        self.assertIsInstance(response, JsonResponse)
        content = json.loads(response.content)
        self.assertIn('error', content)
        self.assertEqual(content['error'], 'Date parameter is missing.')
        mock_get_available_dropoff_times.assert_not_called()

    # Corrected patch path
    @patch('service.ajax.ajax_get_available_dropoff_times_for_date.get_available_dropoff_times')
    def test_invalid_date_format(self, mock_get_available_dropoff_times):
        """
        Test that the view returns a 400 error for an invalid date format.
        """
        request = self.factory.get('/ajax/available-times/?date=2025/06/15') # Invalid format
        response = get_available_dropoff_times_for_date(request)

        self.assertEqual(response.status_code, 400)
        self.assertIsInstance(response, JsonResponse)
        content = json.loads(response.content)
        self.assertIn('error', content)
        # Corrected expected error message to match the view's actual output
        self.assertEqual(content['error'], 'Invalid date format. Use YYYY-MM-DD.')
        mock_get_available_dropoff_times.assert_not_called()

    # Corrected patch path
    @patch('service.ajax.ajax_get_available_dropoff_times_for_date.get_available_dropoff_times')
    def test_valid_date_no_available_times(self, mock_get_available_dropoff_times):
        """
        Test that the view returns an empty list if get_available_dropoff_times
        returns an empty list (e.g., all slots are blocked or no settings).
        """
        # Mock the utility function to return an empty list
        mock_get_available_dropoff_times.return_value = []

        test_date = datetime.date(2025, 6, 20)
        request = self.factory.get(f'/ajax/available-times/?date={test_date.strftime("%Y-%m-%d")}')
        response = get_available_dropoff_times_for_date(request)

        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response, JsonResponse)
        content = json.loads(response.content)
        self.assertIn('available_times', content)
        self.assertEqual(content['available_times'], [])
        # Ensure the utility function was called with the correct date
        mock_get_available_dropoff_times.assert_called_once_with(test_date)

    # Corrected patch path
    @patch('service.ajax.ajax_get_available_dropoff_times_for_date.get_available_dropoff_times')
    def test_valid_date_with_available_times(self, mock_get_available_dropoff_times):
        """
        Test that the view correctly returns formatted available times.
        """
        # Mock the utility function to return a list of times
        mock_times = ["09:00", "09:30", "10:00"]
        mock_get_available_dropoff_times.return_value = mock_times

        test_date = datetime.date(2025, 6, 21)
        request = self.factory.get(f'/ajax/available-times/?date={test_date.strftime("%Y-%m-%d")}')
        response = get_available_dropoff_times_for_date(request)

        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response, JsonResponse)
        content = json.loads(response.content)
        self.assertIn('available_times', content)
        
        expected_formatted_times = [
            {"value": "09:00", "text": "09:00"},
            {"value": "09:30", "text": "09:30"},
            {"value": "10:00", "text": "10:00"},
        ]
        self.assertEqual(content['available_times'], expected_formatted_times)
        mock_get_available_dropoff_times.assert_called_once_with(test_date)

    # Corrected patch path
    @patch('service.ajax.ajax_get_available_dropoff_times_for_date.get_available_dropoff_times')
    def test_only_get_requests_allowed(self, mock_get_available_dropoff_times):
        """
        Test that only GET requests are allowed for this view.
        (The @require_GET decorator handles this).
        """
        test_date = datetime.date(2025, 6, 22)
        request = self.factory.post(f'/ajax/available-times/?date={test_date.strftime("%Y-%m-%d")}')
        response = get_available_dropoff_times_for_date(request)

        # @require_GET decorator returns 405 Method Not Allowed for non-GET requests
        self.assertEqual(response.status_code, 405)
        mock_get_available_dropoff_times.assert_not_called()
