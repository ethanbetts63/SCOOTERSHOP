
from django.test import TestCase
from unittest.mock import patch, MagicMock
from inventory.utils.send_sales_booking_to_mechanicdesk import send_sales_booking_to_mechanicdesk
from inventory.tests.test_helpers.model_factories import SalesBookingFactory, SalesProfileFactory, MotorcycleFactory, PaymentFactory
from django.conf import settings
from decimal import Decimal
import datetime
import requests # Added import

class SendSalesBookingToMechanicdeskTest(TestCase):

    def setUp(self):
        self.sales_profile = SalesProfileFactory(
            name="John Doe",
            email="john.doe@example.com",
            phone_number="1234567890",
            address_line_1="123 Test St",
            address_line_2="Apt 1",
            city="Testville",
            state="TS",
            post_code="1234",
            country="AU",
        )
        self.motorcycle = MotorcycleFactory(
            rego="TEST123",
            brand="Honda",
            model="CBR500R",
            year=2020,
            engine_size=500,
            transmission="manual",
            vin_number="VIN1234567890",
            odometer=10000,
        )
        self.payment = PaymentFactory(amount=Decimal('100.00'), currency='AUD')
        self.sales_booking = SalesBookingFactory(
            sales_profile=self.sales_profile,
            motorcycle=self.motorcycle,
            payment=self.payment,
            sales_booking_reference="SBK-XYZ",
            booking_status="confirmed",
            payment_status="deposit_paid",
            appointment_date=datetime.date(2025, 7, 15),
            appointment_time=datetime.time(10, 30),
            customer_notes="Please check brakes."
        )

    @patch('inventory.utils.send_sales_booking_to_mechanicdesk.requests.post')
    @patch.object(settings, 'MECHANICDESK_BOOKING_TOKEN', 'test_token')
    def test_send_sales_booking_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        result = send_sales_booking_to_mechanicdesk(self.sales_booking)
        self.assertTrue(result)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertIn('token', kwargs['data'])
        self.assertEqual(kwargs['data']['token'], 'test_token')
        self.assertEqual(kwargs['data']['name'], "John Doe")
        self.assertEqual(kwargs['data']['email'], "john.doe@example.com")
        self.assertEqual(kwargs['data']['phone'], "1234567890")
        self.assertIn("--- SALES BOOKING NOTIFICATION ---", kwargs['data']['note'])
        self.assertIn("Booking Reference: SBK-XYZ", kwargs['data']['note'])
        self.assertIn("Customer Notes (from booking): Please check brakes.", kwargs['data']['note'])

    @patch.object(settings, 'MECHANICDESK_BOOKING_TOKEN', None)
    def test_send_sales_booking_no_token(self):
        result = send_sales_booking_to_mechanicdesk(self.sales_booking)
        self.assertFalse(result)

    @patch('inventory.utils.send_sales_booking_to_mechanicdesk.requests.post')
    @patch.object(settings, 'MECHANICDESK_BOOKING_TOKEN', 'test_token')
    def test_send_sales_booking_request_exception(self, mock_post):
        mock_post.side_effect = requests.exceptions.RequestException("Connection error")
        result = send_sales_booking_to_mechanicdesk(self.sales_booking)
        self.assertFalse(result)

    @patch('inventory.utils.send_sales_booking_to_mechanicdesk.requests.post')
    @patch.object(settings, 'MECHANICDESK_BOOKING_TOKEN', 'test_token')
    def test_send_sales_booking_timeout(self, mock_post):
        mock_post.side_effect = requests.exceptions.Timeout("Request timed out")
        result = send_sales_booking_to_mechanicdesk(self.sales_booking)
        self.assertFalse(result)

    @patch('inventory.utils.send_sales_booking_to_mechanicdesk.requests.post')
    @patch.object(settings, 'MECHANICDESK_BOOKING_TOKEN', 'test_token')
    def test_send_sales_booking_general_exception(self, mock_post):
        mock_post.side_effect = Exception("Something unexpected happened")
        result = send_sales_booking_to_mechanicdesk(self.sales_booking)
        self.assertFalse(result)

    @patch('inventory.utils.send_sales_booking_to_mechanicdesk.requests.post')
    @patch.object(settings, 'MECHANICDESK_BOOKING_TOKEN', 'test_token')
    def test_send_sales_booking_no_appointment_time(self, mock_post):
        self.sales_booking.appointment_time = None
        self.sales_booking.save()
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        result = send_sales_booking_to_mechanicdesk(self.sales_booking)
        self.assertTrue(result)
        args, kwargs = mock_post.call_args
        self.assertIn("Appointment Requested (Perth Time):", kwargs['data']['note'])
        self.assertIn("Not specified", kwargs['data']['note'])

    @patch('inventory.utils.send_sales_booking_to_mechanicdesk.requests.post')
    @patch.object(settings, 'MECHANICDESK_BOOKING_TOKEN', 'test_token')
    def test_send_sales_booking_no_appointment_date_or_time(self, mock_post):
        self.sales_booking.appointment_date = None
        self.sales_booking.appointment_time = None
        self.sales_booking.save()
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        result = send_sales_booking_to_mechanicdesk(self.sales_booking)
        self.assertTrue(result)
        args, kwargs = mock_post.call_args
        # When no appointment date/time, it uses current UTC time and doesn't include the specific line
        self.assertNotIn("Appointment Requested (Perth Time):", kwargs['data']['note'])

    @patch('inventory.utils.send_sales_booking_to_mechanicdesk.requests.post')
    @patch.object(settings, 'MECHANICDESK_BOOKING_TOKEN', 'test_token')
    def test_send_sales_booking_no_address_line_2(self, mock_post):
        self.sales_profile.address_line_2 = ""
        self.sales_profile.save()
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        result = send_sales_booking_to_mechanicdesk(self.sales_booking)
        self.assertTrue(result)
        args, kwargs = mock_post.call_args
        # Check that address_line_2 is not included in the formatted address string
        expected_address_part = f"{self.sales_profile.address_line_1}, {self.sales_profile.city}, {self.sales_profile.state} {self.sales_profile.post_code}, {self.sales_profile.country}"
        self.assertIn(f"Customer Address: {expected_address_part}", kwargs['data']['note'])
        
