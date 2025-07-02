from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.contrib.messages import get_messages
from django.utils import timezone
import datetime
from unittest.mock import patch

from service.utils.booking_protection import (
    set_recent_booking_flag,
    check_and_manage_recent_booking_flag,
)


class BookingProtectionUtilTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.request = self.factory.get("/")

        self.request.session = self.client.session

        messages_middleware = "django.contrib.messages.middleware.MessageMiddleware"
        self.middleware = __import__(
            messages_middleware.rsplit(".", 1)[0],
            fromlist=[messages_middleware.rsplit(".", 1)[1]],
        )
        self.middleware.MessageMiddleware(lambda r: None).process_request(self.request)

    def test_set_recent_booking_flag_stores_timestamp(self):

        with patch("django.utils.timezone.now") as mock_now:

            test_time = datetime.datetime(
                2025, 1, 1, 10, 0, 0, tzinfo=datetime.timezone.utc
            )
            mock_now.return_value = test_time

            set_recent_booking_flag(self.request)
            self.assertIn("last_booking_successful_timestamp", self.request.session)
            self.assertEqual(
                self.request.session["last_booking_successful_timestamp"],
                test_time.isoformat(),
            )

    def test_check_and_manage_recent_booking_flag_no_flag(self):

        self.assertNotIn("last_booking_successful_timestamp", self.request.session)
        response = check_and_manage_recent_booking_flag(self.request)
        self.assertIsNone(response)
        self.assertFalse(list(get_messages(self.request)))

    def test_check_and_manage_recent_booking_flag_within_cooling_period(self):

        with patch("django.utils.timezone.now") as mock_now:

            initial_time = datetime.datetime(
                2025, 1, 1, 10, 0, 0, tzinfo=datetime.timezone.utc
            )
            self.request.session["last_booking_successful_timestamp"] = (
                initial_time.isoformat()
            )

            mock_now.return_value = initial_time + datetime.timedelta(minutes=1)

            response = check_and_manage_recent_booking_flag(self.request)

            self.assertIsNotNone(response)
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.url, reverse("service:service"))

            messages = list(get_messages(self.request))
            self.assertEqual(len(messages), 1)
            self.assertIn("You recently completed a booking.", str(messages[0]))

            self.assertIn("last_booking_successful_timestamp", self.request.session)
            self.assertEqual(
                self.request.session["last_booking_successful_timestamp"],
                initial_time.isoformat(),
            )

    def test_check_and_manage_recent_booking_flag_after_cooling_period(self):

        with patch("django.utils.timezone.now") as mock_now:

            initial_time = datetime.datetime(
                2025, 1, 1, 10, 0, 0, tzinfo=datetime.timezone.utc
            )
            self.request.session["last_booking_successful_timestamp"] = (
                initial_time.isoformat()
            )

            mock_now.return_value = initial_time + datetime.timedelta(minutes=3)

            response = check_and_manage_recent_booking_flag(self.request)

            self.assertIsNone(response)
            self.assertNotIn("last_booking_successful_timestamp", self.request.session)
            self.assertFalse(list(get_messages(self.request)))

    def test_check_and_manage_recent_booking_flag_malformed_timestamp(self):

        self.request.session["last_booking_successful_timestamp"] = (
            "not-a-valid-timestamp"
        )

        response = check_and_manage_recent_booking_flag(self.request)

        self.assertIsNone(response)
        self.assertNotIn("last_booking_successful_timestamp", self.request.session)
        self.assertFalse(list(get_messages(self.request)))
