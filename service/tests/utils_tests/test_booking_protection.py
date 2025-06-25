# service/tests/utils/test_booking_protection.py

from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.contrib.messages import get_messages
from django.utils import timezone
import datetime # Import datetime to use datetime.timezone.utc
from unittest.mock import patch

from service.utils.booking_protection import (
    set_recent_booking_flag,
    check_and_manage_recent_booking_flag
)

class BookingProtectionUtilTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.request = self.factory.get('/')
        # Attach a session to the request object, required by Django's messages and session system
        self.request.session = self.client.session
        # Initialize messages middleware for the request for testing messages
        # (Needed because RequestFactory doesn't run full middleware stack)
        messages_middleware = 'django.contrib.messages.middleware.MessageMiddleware'
        self.middleware = __import__(messages_middleware.rsplit('.', 1)[0], fromlist=[messages_middleware.rsplit('.', 1)[1]])
        self.middleware.MessageMiddleware(lambda r: None).process_request(self.request)


    def test_set_recent_booking_flag_stores_timestamp(self):
        """
        Tests that set_recent_booking_flag correctly stores the current timestamp in the session.
        """
        with patch('django.utils.timezone.now') as mock_now:
            # Use datetime.timezone.utc as per your existing tests
            test_time = datetime.datetime(2025, 1, 1, 10, 0, 0, tzinfo=datetime.timezone.utc)
            mock_now.return_value = test_time
            
            set_recent_booking_flag(self.request)
            self.assertIn('last_booking_successful_timestamp', self.request.session)
            self.assertEqual(self.request.session['last_booking_successful_timestamp'], test_time.isoformat())

    def test_check_and_manage_recent_booking_flag_no_flag(self):
        """
        Tests that check_and_manage_recent_booking_flag returns None if no flag exists.
        """
        self.assertNotIn('last_booking_successful_timestamp', self.request.session)
        response = check_and_manage_recent_booking_flag(self.request)
        self.assertIsNone(response)
        self.assertFalse(list(get_messages(self.request))) # No messages should be added

    def test_check_and_manage_recent_booking_flag_within_cooling_period(self):
        """
        Tests that check_and_manage_recent_booking_flag redirects and adds a message
        if the flag is within the cooling-off period.
        """
        with patch('django.utils.timezone.now') as mock_now:
            # Set a timestamp 1 minute ago
            initial_time = datetime.datetime(2025, 1, 1, 10, 0, 0, tzinfo=datetime.timezone.utc)
            self.request.session['last_booking_successful_timestamp'] = initial_time.isoformat()
            
            # Simulate current time being 1 minute after initial_time
            mock_now.return_value = initial_time + datetime.timedelta(minutes=1)

            response = check_and_manage_recent_booking_flag(self.request)
            
            self.assertIsNotNone(response)
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.url, reverse('service:service'))
            
            messages = list(get_messages(self.request))
            self.assertEqual(len(messages), 1)
            self.assertIn("You recently completed a booking.", str(messages[0]))
            
            # Flag should still exist in the session
            self.assertIn('last_booking_successful_timestamp', self.request.session)
            self.assertEqual(self.request.session['last_booking_successful_timestamp'], initial_time.isoformat())

    def test_check_and_manage_recent_booking_flag_after_cooling_period(self):
        """
        Tests that check_and_manage_recent_booking_flag clears the flag and returns None
        if the flag is older than the cooling-off period.
        """
        with patch('django.utils.timezone.now') as mock_now:
            # Set a timestamp 3 minutes ago
            initial_time = datetime.datetime(2025, 1, 1, 10, 0, 0, tzinfo=datetime.timezone.utc)
            self.request.session['last_booking_successful_timestamp'] = initial_time.isoformat()
            
            # Simulate current time being 3 minutes after initial_time
            mock_now.return_value = initial_time + datetime.timedelta(minutes=3)

            response = check_and_manage_recent_booking_flag(self.request)
            
            self.assertIsNone(response)
            self.assertNotIn('last_booking_successful_timestamp', self.request.session) # Flag should be cleared
            self.assertFalse(list(get_messages(self.request))) # No messages should be added

    def test_check_and_manage_recent_booking_flag_malformed_timestamp(self):
        """
        Tests that check_and_manage_recent_booking_flag handles malformed timestamps by clearing the flag.
        """
        self.request.session['last_booking_successful_timestamp'] = 'not-a-valid-timestamp'
        
        response = check_and_manage_recent_booking_flag(self.request)
        
        self.assertIsNone(response)
        self.assertNotIn('last_booking_successful_timestamp', self.request.session) # Flag should be cleared
        self.assertFalse(list(get_messages(self.request))) # No messages should be added

