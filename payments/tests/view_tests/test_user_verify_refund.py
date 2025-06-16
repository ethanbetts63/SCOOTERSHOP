# payments/tests/view_tests/test_user_verify_refund.py

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta, time
from unittest.mock import patch
import uuid
from decimal import Decimal

# Import factories, including for SalesBookings
from payments.tests.test_helpers.model_factories import (
    RefundRequestFactory, HireBookingFactory, ServiceBookingFactory, SalesBookingFactory,
    PaymentFactory, SalesProfileFactory
)

# Define patch paths for all three calculation functions
HIRE_CALC_PATH = 'payments.views.Refunds.user_verify_refund_view.calculate_hire_refund_amount'
SERVICE_CALC_PATH = 'payments.views.Refunds.user_verify_refund_view.calculate_service_refund_amount'
SALES_CALC_PATH = 'payments.views.Refunds.user_verify_refund_view.calculate_sales_refund_amount'
EMAIL_PATH = 'payments.views.Refunds.user_verify_refund_view.send_templated_email'


class UserVerifyRefundViewTests(TestCase):
    """
    Tests for the UserVerifyRefundView, which handles email verification of refund requests.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up non-modified data for all test methods.
        """
        cls.client = Client()

    def setUp(self):
        """
        Set up data for each test method.
        """
        pass

    @patch(HIRE_CALC_PATH)
    @patch(SERVICE_CALC_PATH)
    @patch(SALES_CALC_PATH)
    @patch(EMAIL_PATH)
    def test_successful_verification_hire_booking(
        self, mock_send_email, mock_calc_sales, mock_calc_service, mock_calc_hire
    ):
        """
        Tests successful verification of a refund request for a HireBooking.
        """
        # Setup mock return values for refund calculation
        mock_calc_hire.return_value = {
            'entitled_amount': Decimal('150.00'),
            'details': 'Hire refund calculated successfully.',
        }

        hire_booking = HireBookingFactory(
            payment=PaymentFactory(refund_policy_snapshot={'key': 'value'}),
            booking_reference="HIRE123"
        )
        refund_request = RefundRequestFactory(
            hire_booking=hire_booking,
            payment=hire_booking.payment,
            driver_profile=hire_booking.driver_profile,
            status='unverified',
            token_created_at=timezone.now() - timedelta(hours=1),
        )

        url = reverse('payments:user_verify_refund') + f'?token={refund_request.verification_token}'
        response = self.client.get(url)

        self.assertRedirects(response, reverse('payments:user_verified_refund'))
        refund_request.refresh_from_db()
        self.assertEqual(refund_request.status, 'pending')
        self.assertEqual(refund_request.amount_to_refund, Decimal('150.00'))

        mock_calc_hire.assert_called_once()
        mock_calc_service.assert_not_called()
        mock_calc_sales.assert_not_called()
        mock_send_email.assert_called_once()
        self.assertIn('HIRE123', mock_send_email.call_args.kwargs['subject'])

    @patch(HIRE_CALC_PATH)
    @patch(SERVICE_CALC_PATH)
    @patch(SALES_CALC_PATH)
    @patch(EMAIL_PATH)
    def test_successful_verification_service_booking(
        self, mock_send_email, mock_calc_sales, mock_calc_service, mock_calc_hire
    ):
        """
        Tests successful verification of a refund request for a ServiceBooking.
        """
        mock_calc_service.return_value = {
            'entitled_amount': Decimal('75.00'),
            'details': 'Service refund calculated successfully.',
        }

        service_booking = ServiceBookingFactory(
            payment=PaymentFactory(refund_policy_snapshot={'key': 'value'}),
            service_booking_reference="SERVICE456"
        )
        refund_request = RefundRequestFactory(
            service_booking=service_booking,
            payment=service_booking.payment,
            service_profile=service_booking.service_profile,
            status='unverified',
            token_created_at=timezone.now() - timedelta(hours=1),
        )

        url = reverse('payments:user_verify_refund') + f'?token={refund_request.verification_token}'
        response = self.client.get(url)

        self.assertRedirects(response, reverse('payments:user_verified_refund'))
        refund_request.refresh_from_db()
        self.assertEqual(refund_request.status, 'pending')
        self.assertEqual(refund_request.amount_to_refund, Decimal('75.00'))

        mock_calc_service.assert_called_once()
        mock_calc_hire.assert_not_called()
        mock_calc_sales.assert_not_called()
        mock_send_email.assert_called_once()
        self.assertIn('SERVICE456', mock_send_email.call_args.kwargs['subject'])

    @patch(HIRE_CALC_PATH)
    @patch(SERVICE_CALC_PATH)
    @patch(SALES_CALC_PATH)
    @patch(EMAIL_PATH)
    def test_successful_verification_sales_booking(
        self, mock_send_email, mock_calc_sales, mock_calc_service, mock_calc_hire
    ):
        """
        Tests successful verification of a refund request for a SalesBooking.
        """
        mock_calc_sales.return_value = {
            'entitled_amount': Decimal('500.00'),
            'details': 'Sales refund calculated successfully.',
        }
        sales_booking = SalesBookingFactory(
            payment=PaymentFactory(refund_policy_snapshot={'key': 'value'}),
            sales_booking_reference="SBK789"
        )
        refund_request = RefundRequestFactory(
            sales_booking=sales_booking,
            payment=sales_booking.payment,
            sales_profile=sales_booking.sales_profile,
            status='unverified',
            token_created_at=timezone.now() - timedelta(hours=1),
        )

        url = reverse('payments:user_verify_refund') + f'?token={refund_request.verification_token}'
        response = self.client.get(url)

        self.assertRedirects(response, reverse('payments:user_verified_refund'))
        refund_request.refresh_from_db()
        self.assertEqual(refund_request.status, 'pending')
        self.assertEqual(refund_request.amount_to_refund, Decimal('500.00'))

        mock_calc_sales.assert_called_once()
        mock_calc_hire.assert_not_called()
        mock_calc_service.assert_not_called()
        mock_send_email.assert_called_once()
        self.assertIn('SBK789', mock_send_email.call_args.kwargs['subject'])
        self.assertEqual(mock_send_email.call_args.kwargs['sales_profile'], sales_booking.sales_profile)

    def test_missing_token(self):
        """
        Tests behavior when no token is provided in the URL.
        """
        url = reverse('payments:user_verify_refund')
        response = self.client.get(url, follow=True)

        self.assertRedirects(response, reverse('core:index'), status_code=302, target_status_code=200)
        messages_list = list(response.context['messages'])
        self.assertEqual(len(messages_list), 1)
        self.assertEqual(str(messages_list[0]), "Verification link is missing a token.")

    def test_invalid_token_format(self):
        """
        Tests behavior when an invalid UUID format is provided as a token.
        """
        url = reverse('payments:user_verify_refund') + '?token=invalid-uuid-string'
        response = self.client.get(url, follow=True)

        self.assertRedirects(response, reverse('core:index'), status_code=302, target_status_code=200)
        messages_list = list(response.context['messages'])
        self.assertEqual(len(messages_list), 1)
        self.assertEqual(str(messages_list[0]), "Invalid verification token format.")

    @patch(HIRE_CALC_PATH)
    @patch(SERVICE_CALC_PATH)
    @patch(SALES_CALC_PATH)
    @patch(EMAIL_PATH)
    def test_non_existent_token(self, mock_send_email, mock_calc_sales, mock_calc_service, mock_calc_hire):
        """
        Tests behavior when a valid UUID token is provided but it doesn't match any RefundRequest.
        """
        non_existent_token = uuid.uuid4()
        url = reverse('payments:user_verify_refund') + f'?token={non_existent_token}'
        response = self.client.get(url, follow=True)

        self.assertRedirects(response, reverse('core:index'), status_code=302, target_status_code=200)
        messages_list = list(response.context['messages'])
        self.assertEqual(len(messages_list), 1)
        self.assertEqual(str(messages_list[0]), "The refund request associated with this token does not exist.")
        
        mock_calc_hire.assert_not_called()
        mock_calc_service.assert_not_called()
        mock_calc_sales.assert_not_called()
        mock_send_email.assert_not_called()

    @patch(HIRE_CALC_PATH)
    @patch(SERVICE_CALC_PATH)
    @patch(SALES_CALC_PATH)
    @patch(EMAIL_PATH)
    def test_expired_token(self, mock_send_email, mock_calc_sales, mock_calc_service, mock_calc_hire):
        """
        Tests behavior when the verification token has expired.
        """
        refund_request = RefundRequestFactory(
            status='unverified',
            token_created_at=timezone.now() - timedelta(hours=25)
        )
        url = reverse('payments:user_verify_refund') + f'?token={refund_request.verification_token}'
        response = self.client.get(url, follow=True)

        self.assertRedirects(response, reverse('payments:user_refund_request'), status_code=302, target_status_code=200)
        messages_list = list(response.context['messages'])
        self.assertEqual(len(messages_list), 1)
        self.assertEqual(str(messages_list[0]), "The verification link has expired. Please submit a new refund request.")
        
        refund_request.refresh_from_db()
        self.assertEqual(refund_request.status, 'unverified')
        
        mock_calc_hire.assert_not_called()
        mock_calc_service.assert_not_called()
        mock_calc_sales.assert_not_called()
        mock_send_email.assert_not_called()

    @patch(HIRE_CALC_PATH)
    @patch(SERVICE_CALC_PATH)
    @patch(SALES_CALC_PATH)
    @patch(EMAIL_PATH)
    def test_already_verified_token(self, mock_send_email, mock_calc_sales, mock_calc_service, mock_calc_hire):
        """
        Tests behavior when the refund request has already been verified.
        """
        refund_request = RefundRequestFactory(status='pending') # Already 'pending'
        url = reverse('payments:user_verify_refund') + f'?token={refund_request.verification_token}'
        response = self.client.get(url)

        self.assertRedirects(response, reverse('payments:user_verified_refund'))
        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 1)
        self.assertEqual(str(messages_list[0]), "This refund request has already been verified or processed.")

        mock_calc_hire.assert_not_called()
        mock_calc_service.assert_not_called()
        mock_calc_sales.assert_not_called()
        mock_send_email.assert_not_called()
