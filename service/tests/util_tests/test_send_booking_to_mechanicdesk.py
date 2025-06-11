import requests
from unittest.mock import patch, Mock
from django.test import TestCase, override_settings
from decimal import Decimal
from datetime import date, time
import datetime

# Import models
from service.models import ServiceBooking, ServiceProfile, CustomerMotorcycle

# Import the utility function to be tested
from service.utils.send_booking_to_mechanicdesk import send_booking_to_mechanicdesk

# Import model factories
# Adjust this import path if your test_helpers are located elsewhere
from ..test_helpers.model_factories import (
    ServiceTypeFactory,
    ServiceProfileFactory,
    CustomerMotorcycleFactory,
    ServiceBookingFactory, # We will use this to create a fresh booking instance for each test
)

# Define a dummy token for testing purposes
TEST_MECHANICDESK_TOKEN = 'test-token-1234567890abcdef'

class MechanicDeskIntegrationTests(TestCase):
    """
    Tests for the send_booking_to_mechanicdesk utility function.
    These tests use mocking to avoid actual API calls to MechanicDesk.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up common, non-modifying data for all tests in this class.
        """
        # Create factory instances for related models that will be linked to ServiceBooking
        cls.service_type = ServiceTypeFactory()
        cls.service_profile = ServiceProfileFactory()
        cls.customer_motorcycle = CustomerMotorcycleFactory(service_profile=cls.service_profile)

        # We will create a fresh ServiceBooking instance for each test method
        # using ServiceBookingFactory in the setUp method to ensure clean state.

    def setUp(self):
        """
        Set up for each test method. Ensure a clean state by creating new instances.
        """
        # Create a ServiceBooking instance using the factory, linking it to the pre-created related objects
        self.service_booking = ServiceBookingFactory(
            service_type=self.service_type,
            service_profile=self.service_profile,
            customer_motorcycle=self.customer_motorcycle,
            # Ensure dates and times are set to predictable values for assertions
            service_date=date.today(),
            dropoff_date=date.today(),
            dropoff_time=time(9, 30),
            estimated_pickup_date=date.today() + datetime.timedelta(days=1),
            customer_notes="Regular service and brake check requested."
        )

    @patch('requests.post') # Patch the requests.post method that send_booking_to_mechanicdesk calls
    @override_settings(MECHANICDESK_BOOKING_TOKEN=TEST_MECHANICDESK_TOKEN)
    def test_send_booking_to_mechanicdesk_success(self, mock_post):
        """
        Tests that a successful call to MechanicDesk API returns True and
        sends the correct payload.
        """
        # Configure the mock to simulate a successful HTTP 200 response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "OK" # MechanicDesk usually returns 'OK' for success
        mock_post.return_value = mock_response

        # Call the utility function with the factory-created booking
        result = send_booking_to_mechanicdesk(self.service_booking)

        # Assertions
        self.assertTrue(result) # Should return True on success
        mock_post.assert_called_once() # requests.post should have been called exactly once

        # Verify the arguments passed to requests.post
        args, kwargs = mock_post.call_args
        self.assertEqual(args[0], "https://mechanicdesk.com.au/booking_requests/") # Check the URL

        sent_data = kwargs['data'] # Get the data payload sent

        # Assert correct token is sent
        self.assertEqual(sent_data['token'], TEST_MECHANICDESK_TOKEN)

        # Assert Customer Details
        self.assertEqual(sent_data['name'], self.service_profile.name)
        self.assertEqual(sent_data['email'], self.service_profile.email)
        self.assertEqual(sent_data['phone'], self.service_profile.phone_number)

        # Assert Vehicle Details (mapped from brand/rego)
        self.assertEqual(sent_data['make'], self.customer_motorcycle.brand)
        self.assertEqual(sent_data['model'], self.customer_motorcycle.model)
        self.assertEqual(sent_data['year'], str(self.customer_motorcycle.year))
        self.assertEqual(sent_data['registration_number'], self.customer_motorcycle.rego)

        # Assert Booking Details and formatted dates
        expected_dropoff_date = self.service_booking.dropoff_date.strftime("%d/%m/%Y")
        self.assertEqual(sent_data['drop_off_time'], expected_dropoff_date) # MechanicDesk expects date here

        expected_pickup_date = self.service_booking.estimated_pickup_date.strftime("%d/%m/%Y")
        self.assertEqual(sent_data['pickup_time'], expected_pickup_date) # MechanicDesk expects date here

        expected_note = (
            f"{self.service_booking.customer_notes}\n"
            f"Customer Preferred Drop-off Time: {self.service_booking.dropoff_time.strftime('%H:%M')}"
        )
        self.assertEqual(sent_data['note'], expected_note)


    @patch('requests.post')
    @override_settings(MECHANICDESK_BOOKING_TOKEN=TEST_MECHANICDESK_TOKEN)
    def test_send_booking_to_mechanicdesk_http_error(self, mock_post):
        """
        Tests that an HTTP error response from MechanicDesk results in False.
        """
        # Simulate a 400 Bad Request error
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Invalid Request Data"
        # Ensure raise_for_status() is called and raises an exception
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError('400 Client Error: Bad Request')
        mock_post.return_value = mock_response

        result = send_booking_to_mechanicdesk(self.service_booking)

        self.assertFalse(result) # Should return False on error
        mock_post.assert_called_once()
        mock_response.raise_for_status.assert_called_once() # Verify raise_for_status was triggered


    @patch('requests.post', side_effect=requests.exceptions.Timeout)
    @override_settings(MECHANICDESK_BOOKING_TOKEN=TEST_MECHANICDESK_TOKEN)
    def test_send_booking_to_mechanicdesk_timeout(self, mock_post):
        """
        Tests that a network timeout results in False.
        """
        # requests.post configured to directly raise a Timeout exception
        result = send_booking_to_mechanicdesk(self.service_booking)

        self.assertFalse(result) # Should return False on timeout
        mock_post.assert_called_once()


    @patch('requests.post')
    @override_settings(MECHANICDESK_BOOKING_TOKEN=None) # Override settings to simulate missing token
    def test_send_booking_to_mechanicdesk_no_token(self, mock_post):
        """
        Tests that the function handles a missing MechanicDesk token gracefully.
        """
        result = send_booking_to_mechanicdesk(self.service_booking)

        self.assertFalse(result) # Should return False
        mock_post.assert_not_called() # requests.post should NOT be called if token is missing


    @patch('requests.post')
    @override_settings(MECHANICDESK_BOOKING_TOKEN=TEST_MECHANICDESK_TOKEN)
    def test_send_booking_to_mechanicdesk_no_customer_motorcycle(self, mock_post):
        """
        Tests that the function handles a ServiceBooking without a linked CustomerMotorcycle.
        Vehicle details should be empty in the payload.
        """
        # Create a booking WITHOUT a customer_motorcycle
        self.service_booking_no_moto = ServiceBookingFactory(
            service_type=self.service_type,
            service_profile=self.service_profile,
            customer_motorcycle=None, # Explicitly set to None
            service_date=date.today(),
            dropoff_date=date.today(),
            dropoff_time=time(10, 0),
            estimated_pickup_date=date.today() + datetime.timedelta(days=2),
            customer_notes="Booking without specific motorcycle."
        )

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "OK"
        mock_post.return_value = mock_response

        result = send_booking_to_mechanicdesk(self.service_booking_no_moto)

        self.assertTrue(result)
        mock_post.assert_called_once()

        args, kwargs = mock_post.call_args
        sent_data = kwargs['data']

        # Assert vehicle details are empty strings
        self.assertEqual(sent_data['make'], "")
        self.assertEqual(sent_data['model'], "")
        self.assertEqual(sent_data['year'], "")
        self.assertEqual(sent_data['registration_number'], "")
