
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

    
