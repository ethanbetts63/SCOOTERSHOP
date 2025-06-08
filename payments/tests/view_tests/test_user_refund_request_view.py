# payments/tests/test_user_refund_request_view.py

from django.test import TestCase, Client
from django.urls import reverse
from unittest import mock
from django.contrib.messages import get_messages
from django.utils import timezone
import datetime
from decimal import Decimal

# Import models
from payments.models import RefundRequest, Payment
from hire.models import HireBooking, DriverProfile
from inventory.models import Motorcycle
from dashboard.models import HireSettings

# Import model factories
from hire.tests.test_helpers.model_factories import (
    create_motorcycle, create_driver_profile, create_hire_booking,
    create_payment, create_hire_settings
)


class UserRefundRequestViewTests(TestCase):
    """
    Tests for the UserRefundRequestView.
    """

    def setUp(self):
        """
        Set up test data for UserRefundRequestView tests.
        """
        self.client = Client()
        self.url = reverse('payments:user_refund_request_hire')

        # Ensure HireSettings exist for age validation and other defaults
        self.hire_settings = create_hire_settings()

        # Create a motorcycle
        self.motorcycle = create_motorcycle(
            brand="Yamaha",
            model="MT-07",
            year=2023,
            daily_hire_rate=Decimal('100.00'),
            hourly_hire_rate=Decimal('20.00')
        )

        # Create a driver profile
        self.driver_profile = create_driver_profile(
            name="Test User",
            email="test@example.com",
            phone_number="0412345678",
            date_of_birth=timezone.now().date() - datetime.timedelta(days=365 * 25) # 25 years old
        )

        # Create a payment (associated with a booking)
        self.payment = create_payment(
            amount=Decimal('200.00'),
            currency='AUD',
            status='succeeded',
            driver_profile=self.driver_profile,
            # A refund policy snapshot is required for Payment model
            refund_policy_snapshot={
                'cancellation_upfront_full_refund_days': 7,
                'cancellation_upfront_partial_refund_days': 3,
                'cancellation_upfront_partial_refund_percentage': '50.00',
                'cancellation_upfront_minimal_refund_days': 1,
                'cancellation_upfront_minimal_refund_percentage': '0.00',
                'deposit_enabled': False,
            }
        )

        # Create a confirmed HireBooking that can be refunded
        self.hire_booking = create_hire_booking(
            motorcycle=self.motorcycle,
            driver_profile=self.driver_profile,
            pickup_date=timezone.now().date() + datetime.timedelta(days=10), # 10 days in future
            pickup_time=datetime.time(10, 0),
            return_date=timezone.now().date() + datetime.timedelta(days=12),
            return_time=datetime.time(16, 0),
            payment=self.payment, # Link payment to booking
            amount_paid=self.payment.amount,
            grand_total=self.payment.amount,
            payment_status='paid',
            status='confirmed',
            booking_reference="TESTBOOK123"
        )
        # Ensure the payment is linked back to the hire booking if not done by factory
        self.payment.hire_booking = self.hire_booking
        self.payment.save()


    def test_get_request_displays_form(self):
        """
        Test that a GET request to the UserRefundRequestView displays the form correctly.
        """
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'payments/user_refund_request_hire.html')
        self.assertIn('form', response.context)
        self.assertContains(response, 'Request a Refund')
        self.assertContains(response, 'Please enter your booking details to request a refund.')

    @mock.patch('payments.views.HireRefunds.user_refund_request_view.send_templated_email')
    def test_post_request_valid_data_creates_refund_request_and_sends_email(self, mock_send_email):
        """
        Test that a POST request with valid data creates a RefundRequest
        and sends a verification email.
        """
        initial_refund_request_count = RefundRequest.objects.count()

        post_data = {
            'booking_reference': self.hire_booking.booking_reference,
            'email': self.driver_profile.email,
            'reason': 'Changed my mind about the booking.'
        }

        response = self.client.post(self.url, post_data)

        # Assertions for redirection
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('payments:user_confirmation_refund_request'))

        # Assertions for RefundRequest creation
        self.assertEqual(RefundRequest.objects.count(), initial_refund_request_count + 1)
        refund_request = RefundRequest.objects.first() # Assuming it's the only one created
        self.assertEqual(refund_request.hire_booking, self.hire_booking)
        self.assertEqual(refund_request.payment, self.payment)
        self.assertEqual(refund_request.driver_profile, self.driver_profile)
        self.assertEqual(refund_request.reason, 'Changed my mind about the booking.')
        self.assertEqual(refund_request.status, 'unverified')
        self.assertIsNotNone(refund_request.verification_token)
        self.assertIsNotNone(refund_request.token_created_at)

        # Assertions for email sending
        mock_send_email.assert_called_once()
        call_args, call_kwargs = mock_send_email.call_args
        self.assertIn(self.driver_profile.email, call_kwargs['recipient_list'])
        self.assertIn('Confirm Your Refund Request', call_kwargs['subject'])
        self.assertEqual(call_kwargs['template_name'], 'user_refund_request_verification.html')
        self.assertIn('verification_link', call_kwargs['context'])
        self.assertIn(str(refund_request.verification_token), call_kwargs['context']['verification_link'])

        # Assertions for messages
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), 'Your refund request has been submitted. Please check your email to confirm your request.')
        self.assertEqual(messages[0].tags, 'success')

    @mock.patch('payments.views.HireRefunds.user_refund_request_view.send_templated_email')
    def test_post_request_invalid_data_shows_errors(self, mock_send_email):
        """
        Test that a POST request with invalid data (e.g., non-existent booking reference)
        does not create a RefundRequest and re-renders the form with errors.
        """
        initial_refund_request_count = RefundRequest.objects.count()

        # Invalid booking reference and email combination
        post_data = {
            'booking_reference': 'NONEXISTENT123',
            'email': 'wrong@example.com',
            'reason': 'This should fail.'
        }

        response = self.client.post(self.url, post_data)

        # Assertions for re-rendering
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'payments/user_refund_request_hire.html')
        self.assertIn('form', response.context)

        # Assertions for RefundRequest creation (should not be created)
        self.assertEqual(RefundRequest.objects.count(), initial_refund_request_count)

        # Assertions for email sending (should not be called)
        mock_send_email.assert_not_called()

        # Assertions for form errors
        form = response.context['form']
        self.assertTrue(form.errors)
        self.assertIn('booking_reference', form.errors)
        # Corrected assertion for the exact error message
        self.assertIn('No booking found with this reference number.', form.errors['booking_reference'])

        # No success messages should be present
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 0)

    @mock.patch('payments.views.HireRefunds.user_refund_request_view.send_templated_email')
    def test_post_request_valid_booking_wrong_email_shows_errors(self, mock_send_email):
        """
        Test that a POST request with a valid booking reference but wrong email
        shows errors. (This is handled by the form's clean method).
        """
        initial_refund_request_count = RefundRequest.objects.count()

        post_data = {
            'booking_reference': self.hire_booking.booking_reference,
            'email': 'another_email@example.com',
            'reason': 'Trying with wrong email.'
        }

        response = self.client.post(self.url, post_data)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'payments/user_refund_request_hire.html')
        self.assertIn('form', response.context)
        self.assertEqual(RefundRequest.objects.count(), initial_refund_request_count)
        mock_send_email.assert_not_called()

        form = response.context['form']
        self.assertTrue(form.errors)
        self.assertIn('email', form.errors)
        # Corrected assertion for the exact error message
        self.assertIn('The email address does not match the one registered for this booking.', form.errors['email'])

