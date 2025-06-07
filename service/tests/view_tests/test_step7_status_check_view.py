# service/tests/test_step7_status_check_view.py
from django.test import TestCase
from django.urls import reverse
import uuid
import json
from unittest.mock import patch

from service.models import ServiceBooking
from payments.models import Payment
from ..test_helpers.model_factories import (
    UserFactory,
    ServiceBookingFactory,
    PaymentFactory,
)

# View to be tested
from service.views.user_views.step7_status_check_view import Step7StatusCheckView

class Step7StatusCheckViewTest(TestCase):
    """
    Tests for the ServiceBookingStatusCheckView (AJAX endpoint).
    """

    @classmethod
    def setUpTestData(cls):
        """Set up non-modified objects used by all test methods."""
        cls.user = UserFactory()
        cls.base_url = reverse('service:service_booking_status_check') # Use the correct URL name

    def setUp(self):
        """Set up for each test method."""
        self.client.force_login(self.user)
        ServiceBooking.objects.all().delete()
        Payment.objects.all().delete()

    def test_get_status_ready(self):
        """
        Tests the endpoint when the ServiceBooking has been created successfully.
        """
        payment_intent_id = f"pi_{uuid.uuid4().hex}"
        booking = ServiceBookingFactory(stripe_payment_intent_id=payment_intent_id)

        url = f"{self.base_url}?payment_intent_id={payment_intent_id}"
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data['status'], 'ready')
        self.assertEqual(data['booking_reference'], booking.service_booking_reference)
        self.assertEqual(data['booking_status'], booking.get_booking_status_display())
        # Check that the session is updated with the final reference
        self.assertEqual(self.client.session.get('final_service_booking_reference'), booking.service_booking_reference)

    def test_get_status_processing(self):
        """
        Tests the endpoint when the ServiceBooking doesn't exist yet, but the Payment does.
        """
        payment_intent_id = f"pi_{uuid.uuid4().hex}"
        # Create a Payment object, but no corresponding ServiceBooking
        PaymentFactory(stripe_payment_intent_id=payment_intent_id)

        url = f"{self.base_url}?payment_intent_id={payment_intent_id}"
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data['status'], 'processing')
        self.assertEqual(data['message'], 'Booking finalization is still in progress.')

    def test_get_status_error_finalization_failed(self):
        """
        Tests the endpoint when both ServiceBooking and Payment are missing, indicating a failure.
        """
        payment_intent_id = f"pi_{uuid.uuid4().hex}"
        # Ensure no records exist for this payment_intent_id

        url = f"{self.base_url}?payment_intent_id={payment_intent_id}"
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 500)
        data = response.json()

        self.assertEqual(data['status'], 'error')
        self.assertEqual(data['message'], 'Booking finalization failed. Please contact support for assistance.')

    def test_get_missing_payment_intent_id(self):
        """
        Tests that a 400 error is returned if payment_intent_id is not provided.
        """
        response = self.client.get(self.base_url) # No query parameter

        self.assertEqual(response.status_code, 400)
        data = response.json()
        
        self.assertEqual(data['status'], 'error')
        self.assertEqual(data['message'], 'Payment Intent ID is required.')

    # Correct the patch target to service.models as ServiceBooking is imported from there,
    # and adjust the original patch error to correctly reference the view within its user_views submodule.
    @patch('service.views.user_views.step7_status_check_view.ServiceBooking.objects.get')
    def test_get_generic_exception_returns_500(self, mock_get):
        """
        Tests that any other exception during processing returns a generic 500 error.
        """
        payment_intent_id = f"pi_{uuid.uuid4().hex}"
        mock_get.side_effect = Exception("A database error occurred")

        url = f"{self.base_url}?payment_intent_id={payment_intent_id}"
        response = self.client.get(url)

        self.assertEqual(response.status_code, 500)
        data = response.json()
        
        self.assertEqual(data['status'], 'error')
        self.assertIn('An internal server error occurred', data['message'])

