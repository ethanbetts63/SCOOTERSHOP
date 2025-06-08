# payments/tests/test_user_verify_refund_view.py

from django.test import TestCase, Client
from django.urls import reverse
from unittest import mock
from django.contrib.messages import get_messages
from django.utils import timezone
import datetime
from decimal import Decimal
import uuid
from django.conf import settings # Import settings

# Import models
from payments.models import RefundRequest, Payment
from hire.models import HireBooking, DriverProfile
from inventory.models import Motorcycle
from dashboard.models import HireSettings

# Import model factories
from hire.tests.test_helpers.model_factories import (
    create_motorcycle, create_driver_profile, create_hire_booking,
    create_payment, create_hire_settings, create_refund_request
)


class UserVerifyRefundViewTests(TestCase):
    """
    Tests for the UserVerifyRefundView.
    """

    def setUp(self):
        """
        Set up test data for UserVerifyRefundView tests.
        """
        self.client = Client()
        self.verify_url_name = 'payments:user_verify_refund'
        self.home_url = reverse('core:index')
        self.request_refund_url = reverse('payments:user_refund_request_hire')
        self.verified_refund_confirm_url = reverse('payments:user_verified_refund')

        # Ensure HireSettings exist
        self.hire_settings = create_hire_settings()

        # Create a motorcycle
        self.motorcycle = create_motorcycle(
            brand="Yamaha",
            model="MT-07",
            year=2023,
            daily_hire_rate=Decimal('100.00')
        )

        # Create a driver profile
        self.driver_profile = create_driver_profile(
            name="Test User",
            email="verify_test@example.com",
            date_of_birth=timezone.now().date() - datetime.timedelta(days=365 * 25) # 25 years old
        )

        # Create a payment (associated with a booking)
        self.payment = create_payment(
            amount=Decimal('200.00'),
            currency='AUD',
            status='succeeded',
            driver_profile=self.driver_profile,
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
            payment=self.payment,
            amount_paid=self.payment.amount,
            grand_total=self.payment.amount,
            payment_status='paid',
            status='confirmed',
            booking_reference="VERIFYBOOK123"
        )
        self.payment.hire_booking = self.hire_booking
        self.payment.save()


    @mock.patch('payments.views.HireRefunds.user_verify_refund_view.send_templated_email')
    @mock.patch('payments.views.HireRefunds.user_verify_refund_view.calculate_refund_amount')
    def test_successful_verification(self, mock_calculate_refund, mock_send_email):
        """
        Test that a valid, unexpired token successfully verifies the refund request.
        """
        # Set up mock return values
        mock_calculate_refund.return_value = {
            'entitled_amount': Decimal('100.00'),
            'details': 'Full refund applicable.',
            'days_before_pickup': 10,
            'policy_applied': 'Upfront Full Refund'
        }
        mock_send_email.return_value = True # Simulate successful email sending

        # Create an unverified refund request with token_created_at
        refund_request = create_refund_request(
            hire_booking=self.hire_booking,
            payment=self.payment,
            driver_profile=self.driver_profile,
            status='unverified',
            request_email=self.driver_profile.email,
            token_created_at=timezone.now() - datetime.timedelta(hours=1) # Ensure token is fresh
        )
        verify_url = reverse(self.verify_url_name) + f'?token={str(refund_request.verification_token)}'

        response = self.client.get(verify_url)

        # Assertions for redirection
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.verified_refund_confirm_url)

        # Assertions for RefundRequest status update
        refund_request.refresh_from_db()
        self.assertEqual(refund_request.status, 'pending')

        # Assertions for messages
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Your refund request has been successfully verified!")
        self.assertEqual(messages[0].tags, 'success')

        # Assertions for admin email sending
        mock_calculate_refund.assert_called_once()
        mock_send_email.assert_called_once()
        call_args, call_kwargs = mock_send_email.call_args
        self.assertIn(settings.DEFAULT_FROM_EMAIL, call_kwargs['recipient_list']) # Use imported settings
        self.assertIn('VERIFIED Refund Request', call_kwargs['subject'])
        self.assertEqual(call_kwargs['template_name'], 'admin_refund_request_notification.html')
        self.assertIn('calculated_refund_amount', call_kwargs['context'])
        self.assertIn('admin_refund_link', call_kwargs['context'])


    def test_missing_token(self):
        """
        Test that a GET request without a token results in an error and redirection.
        """
        response = self.client.get(reverse(self.verify_url_name)) # No token parameter

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.home_url)

        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Verification link is missing a token.")
        self.assertEqual(messages[0].tags, 'error')

    def test_invalid_token_format(self):
        """
        Test that a GET request with a malformed token results in an error and redirection.
        """
        verify_url = reverse(self.verify_url_name) + f'?token=not-a-valid-uuid'
        response = self.client.get(verify_url)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.home_url)

        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Invalid verification token format.")
        self.assertEqual(messages[0].tags, 'error')

    @mock.patch('payments.views.HireRefunds.user_verify_refund_view.send_templated_email')
    @mock.patch('payments.views.HireRefunds.user_verify_refund_view.calculate_refund_amount')
    def test_already_verified_request(self, mock_calculate_refund, mock_send_email):
        """
        Test that a request with a token for an already 'pending' or 'approved'
        refund request results in an info message and redirection.
        """
        # Create an already pending refund request
        refund_request = create_refund_request(
            hire_booking=self.hire_booking,
            payment=self.payment,
            driver_profile=self.driver_profile,
            status='pending', # Already pending
            request_email=self.driver_profile.email,
            token_created_at=timezone.now() - datetime.timedelta(hours=1) # Still need a valid timestamp
        )
        verify_url = reverse(self.verify_url_name) + f'?token={str(refund_request.verification_token)}'

        response = self.client.get(verify_url)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.verified_refund_confirm_url)

        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "This refund request has already been verified or processed.")
        self.assertEqual(messages[0].tags, 'info')

        # Assert no status change
        refund_request.refresh_from_db()
        self.assertEqual(refund_request.status, 'pending')

        # Admin email should NOT be sent again
        mock_calculate_refund.assert_not_called()
        mock_send_email.assert_not_called()

    @mock.patch('payments.views.HireRefunds.user_verify_refund_view.send_templated_email')
    @mock.patch('payments.views.HireRefunds.user_verify_refund_view.calculate_refund_amount')
    def test_expired_token(self, mock_calculate_refund, mock_send_email):
        """
        Test that a GET request with an expired token results in an error
        and redirection to the refund request form.
        """
        # Create an unverified refund request with an expired token
        refund_request = create_refund_request(
            hire_booking=self.hire_booking,
            payment=self.payment,
            driver_profile=self.driver_profile,
            status='unverified',
            request_email=self.driver_profile.email,
            token_created_at=timezone.now() - datetime.timedelta(days=2) # Token expired (24 hours validity)
        )
        verify_url = reverse(self.verify_url_name) + f'?token={str(refund_request.verification_token)}'

        response = self.client.get(verify_url)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.request_refund_url)

        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "The verification link has expired. Please submit a new refund request.")
        self.assertEqual(messages[0].tags, 'error')

        # Assert no status change (or remains 'unverified' if not explicitly set to 'expired')
        refund_request.refresh_from_db()
        self.assertEqual(refund_request.status, 'unverified')

        # Admin email should NOT be sent
        mock_calculate_refund.assert_not_called()
        mock_send_email.assert_not_called()

    @mock.patch('payments.views.HireRefunds.user_verify_refund_view.send_templated_email')
    @mock.patch('payments.views.HireRefunds.user_verify_refund_view.calculate_refund_amount')
    def test_non_existent_refund_request(self, mock_calculate_refund, mock_send_email):
        """
        Test that a GET request with a valid UUID token that does not correspond
        to an existing RefundRequest results in an error and redirection.
        """
        non_existent_token = uuid.uuid4()
        verify_url = reverse(self.verify_url_name) + f'?token={str(non_existent_token)}'

        response = self.client.get(verify_url)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.home_url)

        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        # Assert the specific message now that the view catches Http404
        self.assertEqual(str(messages[0]), "The refund request associated with this token does not exist.")
        self.assertEqual(messages[0].tags, 'error')

        # Admin email should NOT be sent
        mock_calculate_refund.assert_not_called()
        mock_send_email.assert_not_called()

    @mock.patch('payments.views.HireRefunds.user_verify_refund_view.send_templated_email')
    @mock.patch('payments.views.HireRefunds.user_verify_refund_view.calculate_refund_amount')
    def test_unexpected_error(self, mock_calculate_refund, mock_send_email):
        """
        Test that an unexpected exception during verification results in an error
        message and redirection to the homepage.
        """
        # Configure mock_calculate_refund to raise an exception
        mock_calculate_refund.side_effect = Exception("Simulated unexpected error during calculation")

        refund_request_for_error = create_refund_request(
            hire_booking=self.hire_booking,
            payment=self.payment, # Use a valid payment, error will come from mock
            driver_profile=self.driver_profile,
            status='unverified',
            request_email=self.driver_profile.email,
            token_created_at=timezone.now() - datetime.timedelta(hours=1)
        )
        verify_url = reverse(self.verify_url_name) + f'?token={str(refund_request_for_error.verification_token)}'

        response = self.client.get(verify_url)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.home_url) # Should redirect to home on unexpected error

        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertIn("An unexpected error occurred during verification:", str(messages[0]))
        self.assertEqual(messages[0].tags, 'error')

        # Admin email should NOT be sent
        mock_calculate_refund.assert_called_once() # The mock should have been called and raised an error
        mock_send_email.assert_not_called()
