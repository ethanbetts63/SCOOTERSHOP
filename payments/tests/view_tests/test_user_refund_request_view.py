# payments/tests/views/test_user_refund_request_view.py

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib import messages
from django.utils import timezone
from unittest.mock import patch, MagicMock
import uuid

# Import the view to be tested
from payments.views.Refunds.user_refund_request_view import UserRefundRequestView

# Import models and factories
from payments.models import RefundRequest
from payments.tests.test_helpers.model_factories import (
    HireBookingFactory, ServiceBookingFactory, SalesBookingFactory,
    UserFactory, DriverProfileFactory, ServiceProfileFactory, SalesProfileFactory,
    PaymentFactory, ServiceTypeFactory # Assuming ServiceBookingFactory needs ServiceType
)

class UserRefundRequestViewTests(TestCase):
    """
    Tests for the UserRefundRequestView.
    This view allows users to submit a refund request.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up non-modified data for all test methods.
        Create sample bookings for testing form validation and linking.
        """
        cls.client = Client()

        # Create sample ServiceType and other dependencies that might be required by factories
        # Ensure that ServiceBookingFactory can create instances without errors.
        # If ServiceBookingFactory depends on ServiceType, ensure it exists.
        cls.service_type = ServiceTypeFactory()


        # Create sample bookings with unique references and associated profiles
        # Hire Booking
        cls.hire_user = UserFactory(email='hire_customer@example.com')
        cls.driver_profile = DriverProfileFactory(user=cls.hire_user)
        cls.hire_booking = HireBookingFactory(
            booking_reference="HIREBOOK123",
            driver_profile=cls.driver_profile, # Correctly linked
            payment=PaymentFactory()
        )

        # Service Booking
        cls.service_user = UserFactory(email='service_customer@example.com')
        cls.service_profile = ServiceProfileFactory(user=cls.service_user)
        cls.service_booking = ServiceBookingFactory(
            service_booking_reference="SERVBOOK456",
            service_profile=cls.service_profile, # Correctly linked
            payment=PaymentFactory(),
            service_type=cls.service_type, # Ensure service_type is provided if required by factory
        )

        # Sales Booking
        cls.sales_user = UserFactory(email='sales_customer@example.com')
        cls.sales_profile = SalesProfileFactory(user=cls.sales_user)
        cls.sales_booking = SalesBookingFactory(
            sales_booking_reference="SALESBOOK789",
            payment=PaymentFactory(),
            sales_profile=cls.sales_profile, # Correctly linked
        )

        # A booking with a non-matching email (for invalid form submission tests)
        cls.mismatch_user = UserFactory(email='actual_customer@example.com')
        cls.mismatch_driver_profile = DriverProfileFactory(user=cls.mismatch_user)
        cls.hire_booking_mismatch_email = HireBookingFactory(
            booking_reference="MISMATCH000",
            driver_profile=cls.mismatch_driver_profile, # Link to the profile with the 'actual_customer@example.com'
            payment=PaymentFactory()
        )

    def test_get_request_displays_form(self):
        """
        Tests that a GET request to the refund request page displays the form correctly.
        """
        response = self.client.get(reverse('payments:user_refund_request'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'payments/user_refund_request.html')
        self.assertIn('form', response.context)
        self.assertContains(response, 'Request a Refund')
        self.assertContains(response, 'Please enter your booking details to request a refund.')

    @patch('payments.views.Refunds.user_refund_request_view.send_templated_email')
    def test_post_request_successful_hire_booking(self, mock_send_email):
        """
        Tests successful submission of a refund request for a HireBooking.
        """
        form_data = {
            'booking_reference': self.hire_booking.booking_reference,
            'request_email': self.hire_user.email, # Use email from the linked user profile
            'reason': 'Changed mind about hire',
        }
        
        # Ensure initial state: no RefundRequest exists
        self.assertEqual(RefundRequest.objects.count(), 0)

        response = self.client.post(reverse('payments:user_refund_request'), form_data)

        # Check redirect and success message
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('payments:user_confirmation_refund_request'))
        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 1)
        self.assertEqual(str(messages_list[0]), 'Your refund request has been submitted. Please check your email to confirm your request.')
        self.assertEqual(messages_list[0].tags, 'success')

        # Check if RefundRequest was created correctly
        self.assertEqual(RefundRequest.objects.count(), 1)
        refund_request = RefundRequest.objects.first()
        self.assertEqual(refund_request.hire_booking, self.hire_booking)
        self.assertEqual(refund_request.service_booking, None)
        self.assertEqual(refund_request.sales_booking, None)
        self.assertEqual(refund_request.request_email, form_data['request_email'])
        self.assertEqual(refund_request.reason, form_data['reason'])
        self.assertEqual(refund_request.status, 'unverified')
        self.assertIsNotNone(refund_request.verification_token)
        self.assertIsNotNone(refund_request.token_created_at)

        # Check if email was sent
        mock_send_email.assert_called_once()
        call_kwargs = mock_send_email.call_args[1] # Keyword arguments
        self.assertIn(form_data['request_email'], call_kwargs['recipient_list'])
        self.assertIn(self.hire_booking.booking_reference, call_kwargs['subject'])
        self.assertEqual(call_kwargs['template_name'], 'user_refund_request_verification.html')
        self.assertEqual(call_kwargs['booking'], self.hire_booking)
        self.assertEqual(call_kwargs['driver_profile'], self.driver_profile)
        self.assertIsNone(call_kwargs['service_profile'])
        self.assertIsNone(call_kwargs['sales_profile'])
        self.assertIn('verification_link', call_kwargs['context'])
        self.assertIn(str(refund_request.verification_token), call_kwargs['context']['verification_link'])


    @patch('payments.views.Refunds.user_refund_request_view.send_templated_email')
    def test_post_request_successful_service_booking(self, mock_send_email):
        """
        Tests successful submission of a refund request for a ServiceBooking.
        """
        form_data = {
            'booking_reference': self.service_booking.service_booking_reference,
            'request_email': self.service_user.email, # Use email from the linked user profile
            'reason': 'Service not needed anymore',
        }
        
        self.assertEqual(RefundRequest.objects.count(), 0) # Ensure clean slate

        response = self.client.post(reverse('payments:user_refund_request'), form_data)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('payments:user_confirmation_refund_request'))
        self.assertEqual(RefundRequest.objects.count(), 1)
        refund_request = RefundRequest.objects.first()
        self.assertEqual(refund_request.service_booking, self.service_booking)
        self.assertEqual(refund_request.hire_booking, None)
        self.assertEqual(refund_request.sales_booking, None)
        self.assertEqual(refund_request.request_email, form_data['request_email'])
        self.assertEqual(refund_request.reason, form_data['reason'])
        self.assertEqual(refund_request.status, 'unverified')

        mock_send_email.assert_called_once()
        call_kwargs = mock_send_email.call_args[1]
        self.assertIn(form_data['request_email'], call_kwargs['recipient_list'])
        self.assertIn(self.service_booking.service_booking_reference, call_kwargs['subject'])
        self.assertEqual(call_kwargs['booking'], self.service_booking)
        self.assertEqual(call_kwargs['service_profile'], self.service_profile)
        self.assertIsNone(call_kwargs['driver_profile'])
        self.assertIsNone(call_kwargs['sales_profile'])


    @patch('payments.views.Refunds.user_refund_request_view.send_templated_email')
    def test_post_request_successful_sales_booking(self, mock_send_email):
        """
        Tests successful submission of a refund request for a SalesBooking.
        """
        form_data = {
            'booking_reference': self.sales_booking.sales_booking_reference,
            'request_email': self.sales_user.email, # Use email from SalesProfile's linked user
            'reason': 'Decided against purchase',
        }
        
        self.assertEqual(RefundRequest.objects.count(), 0) # Ensure clean slate

        response = self.client.post(reverse('payments:user_refund_request'), form_data)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('payments:user_confirmation_refund_request'))
        self.assertEqual(RefundRequest.objects.count(), 1)
        refund_request = RefundRequest.objects.first()
        self.assertEqual(refund_request.sales_booking, self.sales_booking)
        self.assertEqual(refund_request.hire_booking, None)
        self.assertEqual(refund_request.service_booking, None)
        self.assertEqual(refund_request.request_email, form_data['request_email'])
        self.assertEqual(refund_request.reason, form_data['reason'])
        self.assertEqual(refund_request.status, 'unverified')

        mock_send_email.assert_called_once()
        call_kwargs = mock_send_email.call_args[1]
        self.assertIn(form_data['request_email'], call_kwargs['recipient_list'])
        self.assertIn(self.sales_booking.sales_booking_reference, call_kwargs['subject'])
        self.assertEqual(call_kwargs['booking'], self.sales_booking)
        self.assertEqual(call_kwargs['sales_profile'], self.sales_profile)
        self.assertIsNone(call_kwargs['driver_profile'])
        self.assertIsNone(call_kwargs['service_profile'])

    def test_post_request_invalid_form_missing_data(self):
        """
        Tests submission with missing required data in the form.
        """
        form_data = {
            'booking_reference': '', # Missing
            'request_email': 'test@example.com',
            'reason': 'Some reason',
        }
        
        response = self.client.post(reverse('payments:user_refund_request'), form_data)

        # Should render the form again with errors, no redirect
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'payments/user_refund_request.html')
        self.assertIn('form', response.context)
        self.assertFalse(response.context['form'].is_valid())
        self.assertIn('This field is required.', response.context['form'].errors['booking_reference'][0])
        self.assertContains(response, 'Please correct the errors below and try again.')
        self.assertEqual(RefundRequest.objects.count(), 0) # No object created

    def test_post_request_invalid_form_no_matching_booking(self):
        """
        Tests submission with a booking reference that does not exist.
        """
        form_data = {
            'booking_reference': 'NONEXISTENTREF',
            'request_email': 'test@example.com',
            'reason': 'Some reason',
        }
        
        response = self.client.post(reverse('payments:user_refund_request'), form_data)

        # Should render the form again with errors, no redirect
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'payments/user_refund_request.html')
        self.assertIn('form', response.context)
        self.assertFalse(response.context['form'].is_valid())
        # Corrected: Access non_field_errors as this is likely a form-wide error
        self.assertIn('No booking found with this reference and email.', response.context['form'].non_field_errors()[0])
        self.assertEqual(RefundRequest.objects.count(), 0) # No object created

    def test_post_request_invalid_form_email_mismatch(self):
        """
        Tests submission with a valid booking reference but non-matching email.
        """
        form_data = {
            'booking_reference': self.hire_booking_mismatch_email.booking_reference, # Booking exists
            'request_email': 'wrong_email@example.com', # But this email doesn't match the linked profile's user email
            'reason': 'Some reason',
        }
        
        response = self.client.post(reverse('payments:user_refund_request'), form_data)

        # Should render the form again with errors, no redirect
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'payments/user_refund_request.html')
        self.assertIn('form', response.context)
        self.assertFalse(response.context['form'].is_valid())
        # Corrected: Access non_field_errors as this is likely a form-wide error
        self.assertIn('No booking found with this reference and email.', response.context['form'].non_field_errors()[0])
        self.assertEqual(RefundRequest.objects.count(), 0) # No object created

    @patch('payments.views.Refunds.user_refund_request_view.send_templated_email')
    def test_post_request_creates_unique_token(self, mock_send_email):
        """
        Tests that each successful submission creates a unique verification token.
        """
        form_data_1 = {
            'booking_reference': self.hire_booking.booking_reference,
            'request_email': self.hire_user.email,
            'reason': 'Test 1',
        }
        # Create a new service booking for the second request to ensure isolation and a different token
        # Ensure that ServiceType is provided if ServiceBookingFactory needs it.
        service_user_2 = UserFactory(email='service_customer_2@example.com')
        service_profile_2 = ServiceProfileFactory(user=service_user_2)
        service_booking_2 = ServiceBookingFactory(
            service_booking_reference="SERVBOOKXYZ",
            service_profile=service_profile_2, # Corrected: link to profile
            service_type=self.service_type, # Provide service_type
            payment=PaymentFactory()
        )
        form_data_2 = {
            'booking_reference': service_booking_2.service_booking_reference,
            'request_email': service_user_2.email,
            'reason': 'Test 2',
        }

        response1 = self.client.post(reverse('payments:user_refund_request'), form_data_1)
        self.assertEqual(response1.status_code, 302) # Ensure first request was successful
        token1 = RefundRequest.objects.get(request_email=self.hire_user.email).verification_token
        
        # Ensure the mock is reset between calls if you want to assert call_count precisely for each.
        # Or, just ensure two calls were made in total.
        mock_send_email.reset_mock() 
        RefundRequest.objects.all().delete() # Clean up DB for next request to ensure a new object is created


        response2 = self.client.post(reverse('payments:user_refund_request'), form_data_2)
        self.assertEqual(response2.status_code, 302) # Ensure second request was successful
        token2 = RefundRequest.objects.get(request_email=service_user_2.email).verification_token

        self.assertNotEqual(token1, token2)
        self.assertEqual(mock_send_email.call_count, 1) # One call for the second request
