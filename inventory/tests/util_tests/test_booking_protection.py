
from django.test import TestCase, RequestFactory

from inventory.utils.booking_protection import set_recent_booking_flag

class BookingProtectionTests(TestCase):

    def setUp(self):
        self.factory = RequestFactory()

    def test_set_recent_booking_flag(self):
        request = self.factory.get('/')
        request.session = {}
        set_recent_booking_flag(request)
        self.assertIn('last_sales_booking_timestamp', request.session)
        self.assertIsNotNone(request.session['last_sales_booking_timestamp'])

    
