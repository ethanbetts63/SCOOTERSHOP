from django.test import TestCase, RequestFactory
from django.http import JsonResponse
import datetime
import json
from unittest.mock import patch
from service.decorators import admin_required
from users.models import User

from service.ajax.ajax_get_available_dropoff_times_for_date import (
    get_available_dropoff_times_for_date,
)


class AjaxGetAvailableDropoffTimesForDateTest(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username='testuser', password='password', is_staff=True)

    @patch(
        "service.ajax.ajax_get_available_dropoff_times_for_date.get_available_dropoff_times"
    )
    def test_missing_date_parameter(self, mock_get_available_dropoff_times):
        request = self.factory.get("/ajax/available-times/")
        request.user = self.user
        response = get_available_dropoff_times_for_date(request)

        self.assertEqual(response.status_code, 400)
        self.assertIsInstance(response, JsonResponse)
        content = json.loads(response.content)
        self.assertIn("error", content)
        self.assertEqual(content["error"], "Date parameter is missing.")
        mock_get_available_dropoff_times.assert_not_called()

    @patch(
        "service.ajax.ajax_get_available_dropoff_times_for_date.get_available_dropoff_times"
    )
    def test_invalid_date_format(self, mock_get_available_dropoff_times):
        request = self.factory.get("/ajax/available-times/?date=2025/06/15")
        request.user = self.user
        response = get_available_dropoff_times_for_date(request)

        self.assertEqual(response.status_code, 400)
        self.assertIsInstance(response, JsonResponse)
        content = json.loads(response.content)
        self.assertIn("error", content)

        self.assertEqual(content["error"], "Invalid date format. Use YYYY-MM-DD.")
        mock_get_available_dropoff_times.assert_not_called()

    @patch(
        "service.ajax.ajax_get_available_dropoff_times_for_date.get_available_dropoff_times"
    )
    def test_valid_date_no_available_times(self, mock_get_available_dropoff_times):
        mock_get_available_dropoff_times.return_value = []

        test_date = datetime.date(2025, 6, 20)
        request = self.factory.get(
            f'/ajax/available-times/?date={test_date.strftime("%Y-%m-%d")}'
        )
        request.user = self.user
        response = get_available_dropoff_times_for_date(request)

        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response, JsonResponse)
        content = json.loads(response.content)
        self.assertIn("available_times", content)
        self.assertEqual(content["available_times"], [])

        mock_get_available_dropoff_times.assert_called_once_with(test_date)

    @patch(
        "service.ajax.ajax_get_available_dropoff_times_for_date.get_available_dropoff_times"
    )
    def test_valid_date_with_available_times(self, mock_get_available_dropoff_times):
        mock_times = ["09:00", "09:30", "10:00"]
        mock_get_available_dropoff_times.return_value = mock_times

        test_date = datetime.date(2025, 6, 21)
        request = self.factory.get(
            f'/ajax/available-times/?date={test_date.strftime("%Y-%m-%d")}'
        )
        request.user = self.user
        response = get_available_dropoff_times_for_date(request)

        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response, JsonResponse)
        content = json.loads(response.content)
        self.assertIn("available_times", content)

        expected_formatted_times = [
            {"value": "09:00", "text": "09:00"},
            {"value": "09:30", "text": "09:30"},
            {"value": "10:00", "text": "10:00"},
        ]
        self.assertEqual(content["available_times"], expected_formatted_times)
        mock_get_available_dropoff_times.assert_called_once_with(test_date)

    @patch(
        "service.ajax.ajax_get_available_dropoff_times_for_date.get_available_dropoff_times"
    )
    def test_only_get_requests_allowed(self, mock_get_available_dropoff_times):
        test_date = datetime.date(2025, 6, 22)
        request = self.factory.post(
            f'/ajax/available-times/?date={test_date.strftime("%Y-%m-%d")}'
        )
        request.user = self.user
        response = get_available_dropoff_times_for_date(request)

        self.assertEqual(response.status_code, 405)
        mock_get_available_dropoff_times.assert_not_called()
