
from django.test import TestCase, RequestFactory
from django.contrib.messages import get_messages
from django.urls import reverse
from django.utils import timezone
import datetime
from unittest.mock import patch, MagicMock
from django.http import HttpResponseRedirect

from inventory.utils.booking_protection import set_recent_booking_flag, check_and_manage_recent_booking_flag

class BookingProtectionTests(TestCase):

    def setUp(self):
        self.factory = RequestFactory()

    def test_set_recent_booking_flag(self):
        request = self.factory.get('/')
        request.session = {}
        set_recent_booking_flag(request)
        self.assertIn('last_sales_booking_timestamp', request.session)
        self.assertIsNotNone(request.session['last_sales_booking_timestamp'])

    @patch('django.utils.timezone.now')
    @patch('inventory.utils.booking_protection.redirect')
    def test_check_and_manage_recent_booking_flag_within_cooling_off_period(self, mock_redirect, mock_now):
        request = self.factory.get('/')
        request.session = {}
        
        now = timezone.now()
        past_time = now - datetime.timedelta(minutes=1)
        request.session['last_sales_booking_timestamp'] = past_time.isoformat()
        
        # Mock timezone.now() to be current time
        mock_now.return_value = now

        # Configure the mock redirect to return a mock HttpResponseRedirect
        mock_redirect.return_value = HttpResponseRedirect(reverse('inventory:used'))

        response = check_and_manage_recent_booking_flag(request)
        
        # Assert that a redirect response is returned
        self.assertIsInstance(response, HttpResponseRedirect)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('inventory:used'))
        
        # Check that redirect was called with the correct arguments
        mock_redirect.assert_called_once_with(reverse('inventory:used'))

        # Check messages
        messages = list(get_messages(request))
        self.assertEqual(len(messages), 1)
        self.assertIn('You recently completed a purchase or reservation.', str(messages[0]))
        
        # The flag should still be in the session if a redirect occurred
        self.assertIn('last_sales_booking_timestamp', request.session)

    @patch('django.utils.timezone.now')
    def test_check_and_manage_recent_booking_flag_after_cooling_off_period(self, mock_now):
        request = self.factory.get('/')
        request.session = {}
        
        # Set a timestamp 3 minutes ago
        past_time = timezone.now() - datetime.timedelta(minutes=3)
        request.session['last_sales_booking_timestamp'] = past_time.isoformat()

        # Mock timezone.now() to be current time
        mock_now.return_value = timezone.now()

        response = check_and_manage_recent_booking_flag(request)
        self.assertIsNone(response)
        self.assertNotIn('last_sales_booking_timestamp', request.session) # Flag should be removed

    def test_check_and_manage_recent_booking_flag_no_flag(self):
        request = self.factory.get('/')
        request.session = {}
        response = check_and_manage_recent_booking_flag(request)
        self.assertIsNone(response)
        self.assertNotIn('last_sales_booking_timestamp', request.session)

    def test_check_and_manage_recent_booking_flag_invalid_timestamp(self):
        request = self.factory.get('/')
        request.session = {'last_sales_booking_timestamp': 'invalid-timestamp'}
        response = check_and_manage_recent_booking_flag(request)
        self.assertIsNone(response)
        self.assertNotIn('last_sales_booking_timestamp', request.session)
