# inventory/tests/view_tests/user_view_tests/test_initiate_booking_process_view.py

from django.test import TestCase, Client
from django.urls import reverse
from django.db import transaction

from inventory.models import Motorcycle, TempSalesBooking, InventorySettings
from ...test_helpers.model_factories import MotorcycleFactory, InventorySettingsFactory

class InitiateBookingProcessViewTest(TestCase):
    """
    Tests for the InitiateBookingProcessView.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up common data for all tests in this class.
        """
        cls.client = Client()

        # Ensure a singleton InventorySettings instance exists as it influences view logic
        cls.inventory_settings = InventorySettingsFactory()

        # Create a test motorcycle
        cls.motorcycle = MotorcycleFactory(is_available=True)

        # URL for initiating a booking for the test motorcycle
        cls.initiate_booking_url = reverse('inventory:initiate_booking', kwargs={'pk': cls.motorcycle.pk})

    def test_post_request_creates_temp_booking_deposit_flow(self):
        """
        Test that a POST request with 'deposit_required_for_flow': 'true'
        correctly creates a TempSalesBooking and redirects.
        """
        initial_temp_booking_count = TempSalesBooking.objects.count()

        data = {
            'deposit_required_for_flow': 'true',
            'request_viewing': 'false', # Default for this test
        }
        response = self.client.post(self.initiate_booking_url, data)

        # Assert a new TempSalesBooking object was created
        self.assertEqual(TempSalesBooking.objects.count(), initial_temp_booking_count + 1)

        # Retrieve the newly created temp booking
        temp_booking = TempSalesBooking.objects.latest('created_at')

        # Assert correct attributes of the temp booking
        self.assertEqual(temp_booking.motorcycle, self.motorcycle)
        self.assertTrue(temp_booking.deposit_required_for_flow)
        self.assertFalse(temp_booking.request_viewing)
        self.assertEqual(temp_booking.booking_status, 'pending_details')

        # Assert redirect to step1_sales_profile
        self.assertRedirects(response, reverse('inventory:step1_sales_profile'))

        # Assert temp_booking ID is stored in session
        self.assertIn('current_temp_booking_id', self.client.session)
        self.assertEqual(self.client.session['current_temp_booking_id'], temp_booking.pk)


    def test_post_request_creates_temp_booking_enquiry_flow(self):
        """
        Test that a POST request with 'deposit_required_for_flow': 'false'
        correctly creates a TempSalesBooking (enquiry flow) and redirects.
        """
        initial_temp_booking_count = TempSalesBooking.objects.count()

        data = {
            'deposit_required_for_flow': 'false',
            'request_viewing': 'false', # Default for this test
        }
        response = self.client.post(self.initiate_booking_url, data)

        self.assertEqual(TempSalesBooking.objects.count(), initial_temp_booking_count + 1)

        temp_booking = TempSalesBooking.objects.latest('created_at')
        self.assertEqual(temp_booking.motorcycle, self.motorcycle)
        self.assertFalse(temp_booking.deposit_required_for_flow)
        self.assertFalse(temp_booking.request_viewing)
        self.assertEqual(temp_booking.booking_status, 'pending_details')

        self.assertRedirects(response, reverse('inventory:step1_sales_profile'))
        self.assertIn('current_temp_booking_id', self.client.session)
        self.assertEqual(self.client.session['current_temp_booking_id'], temp_booking.pk)

    def test_post_request_creates_temp_booking_with_viewing_request(self):
        """
        Test that a POST request with 'request_viewing': 'true'
        correctly creates a TempSalesBooking with request_viewing flag set.
        """
        initial_temp_booking_count = TempSalesBooking.objects.count()

        data = {
            'deposit_required_for_flow': 'false', # Viewing usually implies deposit-less enquiry
            'request_viewing': 'true',
        }
        response = self.client.post(self.initiate_booking_url, data)

        self.assertEqual(TempSalesBooking.objects.count(), initial_temp_booking_count + 1)

        temp_booking = TempSalesBooking.objects.latest('created_at')
        self.assertEqual(temp_booking.motorcycle, self.motorcycle)
        self.assertFalse(temp_booking.deposit_required_for_flow)
        self.assertTrue(temp_booking.request_viewing)
        self.assertEqual(temp_booking.booking_status, 'pending_details')

        self.assertRedirects(response, reverse('inventory:step1_sales_profile'))
        self.assertIn('current_temp_booking_id', self.client.session)
        self.assertEqual(self.client.session['current_temp_booking_id'], temp_booking.pk)


    def test_post_request_non_existent_motorcycle_pk(self):
        """
        Test that a POST request with a non-existent motorcycle PK returns a 404.
        """
        non_existent_pk = self.motorcycle.pk + 999
        url = reverse('inventory:initiate_booking', kwargs={'pk': non_existent_pk})

        data = {
            'deposit_required_for_flow': 'false',
            'request_viewing': 'false',
        }
        response = self.client.post(url, data)

        # Assert status code is 404
        self.assertEqual(response.status_code, 404)
        # Optionally, check the content of the 404 page if your custom 404 page has specific text
        # self.assertContains(response, "Motorcycle not found", status_code=404) # Or use assertIn for byte content
