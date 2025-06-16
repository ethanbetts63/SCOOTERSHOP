# payments/tests/view_tests/test_user_refund_request_view.py

from django.test import TestCase, Client
from django.urls import reverse
from django.core import mail
from unittest.mock import patch
from decimal import Decimal

from payments.models import RefundRequest
from payments.tests.test_helpers.model_factories import (
    PaymentFactory,
    HireBookingFactory,
    DriverProfileFactory,
    SalesBookingFactory,
    SalesProfileFactory,
    ServiceBookingFactory,
    ServiceProfileFactory,
    UserFactory
)

# Correct path for patching the imported function
PATCH_PATH = 'payments.views.Refunds.user_refund_request_view.send_templated_email'

class UserRefundRequestViewTests(TestCase):
    """
    Tests for the UserRefundRequestView (user-facing).
    """

    def setUp(self):
        """Set up test data and client for all tests."""
        self.client = Client()
        self.user = UserFactory()

        # Profiles for different booking types
        self.driver_profile = DriverProfileFactory(email='hire.customer@example.com')
        self.service_profile = ServiceProfileFactory(email='service.customer@example.com', user=self.user)
        self.sales_profile = SalesProfileFactory(email='sales.customer@example.com', user=self.user)

        # HIRE BOOKING SETUP
        payment_hire = PaymentFactory(status='succeeded', driver_profile=self.driver_profile)
        self.hire_booking = HireBookingFactory(payment=payment_hire, driver_profile=self.driver_profile)
        payment_hire.hire_booking = self.hire_booking
        payment_hire.save()

        # SERVICE BOOKING SETUP
        payment_service = PaymentFactory(status='succeeded', service_customer_profile=self.service_profile)
        self.service_booking = ServiceBookingFactory(payment=payment_service, service_profile=self.service_profile)
        payment_service.service_booking = self.service_booking
        payment_service.save()

        # SALES BOOKING SETUP
        payment_sales = PaymentFactory(status='succeeded', sales_customer_profile=self.sales_profile)
        self.sales_booking = SalesBookingFactory(payment=payment_sales, sales_profile=self.sales_profile)
        payment_sales.sales_booking = self.sales_booking
        payment_sales.save()

        self.refund_request_url = reverse('payments:user_refund_request')

    def test_get_refund_request_page(self):
        """Test that the refund request page loads correctly with a GET request."""
        response = self.client.get(self.refund_request_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'payments/user_refund_request.html')
        self.assertIn('form', response.context)
        self.assertIn('Request a Refund', str(response.content))

    @patch(PATCH_PATH)
    def test_post_successful_hire_refund_request(self, mock_send_email):
        """Test a successful POST request for a HIRE booking."""
        form_data = {
            'booking_reference': self.hire_booking.booking_reference,
            'email': self.driver_profile.email,
            'reason': 'Test hire reason'
        }
        
        response = self.client.post(self.refund_request_url, form_data)
        
        # Check for successful redirection
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('payments:user_confirmation_refund_request'))
        
        # Check that a RefundRequest object was created
        self.assertEqual(RefundRequest.objects.count(), 1)
        refund_request = RefundRequest.objects.first()
        self.assertEqual(refund_request.hire_booking, self.hire_booking)
        self.assertEqual(refund_request.status, 'unverified')
        
        # Check that the email sending function was called
        mock_send_email.assert_called_once()
        args, kwargs = mock_send_email.call_args
        self.assertEqual(kwargs['recipient_list'], [self.driver_profile.email.lower()])
        self.assertIn(self.hire_booking.booking_reference, kwargs['subject'])

    @patch(PATCH_PATH)
    def test_post_successful_service_refund_request(self, mock_send_email):
        """Test a successful POST request for a SERVICE booking."""
        form_data = {
            'booking_reference': self.service_booking.service_booking_reference,
            'email': self.service_profile.email,
            'reason': 'Test service reason'
        }
        
        response = self.client.post(self.refund_request_url, form_data)
        
        self.assertEqual(response.status_code, 302)
        self.assertEqual(RefundRequest.objects.count(), 1)
        refund_request = RefundRequest.objects.first()
        self.assertEqual(refund_request.service_booking, self.service_booking)
        self.assertEqual(refund_request.status, 'unverified')
        
        mock_send_email.assert_called_once()
        args, kwargs = mock_send_email.call_args
        self.assertEqual(kwargs['recipient_list'], [self.service_profile.email.lower()])
        self.assertIn(self.service_booking.service_booking_reference, kwargs['subject'])

    @patch(PATCH_PATH)
    def test_post_successful_sales_refund_request(self, mock_send_email):
        """Test a successful POST request for a SALES booking."""
        form_data = {
            'booking_reference': self.sales_booking.sales_booking_reference,
            'email': self.sales_profile.email,
            'reason': 'Test sales reason'
        }
        
        response = self.client.post(self.refund_request_url, form_data)
        
        self.assertEqual(response.status_code, 302)
        self.assertEqual(RefundRequest.objects.count(), 1)
        refund_request = RefundRequest.objects.first()
        self.assertEqual(refund_request.sales_booking, self.sales_booking)
        self.assertEqual(refund_request.status, 'unverified')
        
        mock_send_email.assert_called_once()
        args, kwargs = mock_send_email.call_args
        self.assertEqual(kwargs['recipient_list'], [self.sales_profile.email.lower()])
        self.assertIn(self.sales_booking.sales_booking_reference, kwargs['subject'])
        
    @patch(PATCH_PATH)
    def test_post_invalid_form_data(self, mock_send_email):
        """Test a POST request with invalid data (e.g., email mismatch)."""
        form_data = {
            'booking_reference': self.hire_booking.booking_reference,
            'email': 'wrong@email.com',
            'reason': 'This should fail'
        }
        
        response = self.client.post(self.refund_request_url, form_data)
        
        # Check that the page is re-rendered with errors
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'payments/user_refund_request.html')
        self.assertIn('form', response.context)
        self.assertTrue(response.context['form'].errors)
        
        # Check that no RefundRequest was created and no email was sent
        self.assertEqual(RefundRequest.objects.count(), 0)
        mock_send_email.assert_not_called()
        
    @patch(PATCH_PATH)
    def test_post_shows_message_on_success(self, mock_send_email):
        """Test that a success message is shown after a valid submission."""
        form_data = {
            'booking_reference': self.hire_booking.booking_reference,
            'email': self.driver_profile.email,
            'reason': 'Checking for success message'
        }
        
        response = self.client.post(self.refund_request_url, form_data, follow=True) # follow=True to check the redirected page
        
        # Check the final page after redirection
        self.assertEqual(response.status_code, 200)
        messages = list(response.context['messages'])
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), 'Your refund request has been submitted. Please check your email to confirm your request.')

