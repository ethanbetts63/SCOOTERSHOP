# payments/tests/test_user_verify_refund_view.py

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.messages import get_messages
from django.utils import timezone
from datetime import timedelta, time
from unittest.mock import patch, MagicMock
import uuid
from decimal import Decimal

# Import factories
from payments.tests.test_helpers.model_factories import (
    RefundRequestFactory, HireBookingFactory, ServiceBookingFactory,
    PaymentFactory, DriverProfileFactory, ServiceProfileFactory
)
from payments.models import RefundRequest

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
        # Ensure a fresh RefundPolicySettings exists for refund calculation mocks
        # In a real scenario, this might be pre-created by a fixture or migration
        # For tests, we ensure it exists with default-like values if needed by mocks.
        # However, since refund calculation utilities are mocked, the actual policy
        # settings are less critical here than ensuring the RefundRequest is valid.

        # Reset mocks before each test if they were used in previous tests
        # This is particularly important for functions patched in individual tests.
        pass

    @patch('payments.views.Refunds.calculate_hire_refund_amount')
    @patch('payments.views.Refunds.calculate_service_refund_amount')
    @patch('payments.views.Refunds.send_templated_email')
    def test_successful_verification_hire_booking(
        self, mock_send_templated_email, mock_calculate_service_refund, mock_calculate_hire_refund
    ):
        """
        Tests successful verification of a refund request for a HireBooking.
        Verifies status update, refund calculation, and admin email sending.
        """
        # Setup mock return values for refund calculation
        mock_calculate_hire_refund.return_value = {
            'entitled_amount': Decimal('150.00'),
            'details': 'Hire refund calculated successfully.',
            'policy_applied': 'Full Payment Policy',
            'days_before_dropoff': 10
        }
        mock_calculate_service_refund.return_value = {
            'entitled_amount': Decimal('0.00'),
            'details': 'No service booking involved.',
            'policy_applied': 'N/A',
            'days_before_dropoff': 'N/A'
        }

        # Create a HireBooking and associated Payment and DriverProfile
        # Using pickup_date and return_date for HireBooking
        hire_booking = HireBookingFactory(
            payment=PaymentFactory(
                amount=Decimal('300.00'),
                status='succeeded',
                refund_policy_snapshot={'key': 'value'} # Example snapshot
            ),
            pickup_date=timezone.now().date() + timedelta(days=5), # Set a realistic pickup date
            pickup_time=time(10,0),
            return_date=timezone.now().date() + timedelta(days=15), # Set a realistic return date
            booking_reference="HIRE123"
        )
        driver_profile = hire_booking.driver_profile # Get the one created by the booking factory

        # Create an unverified RefundRequest
        refund_request = RefundRequestFactory(
            hire_booking=hire_booking,
            service_booking=None, # Ensure it's a hire booking refund
            payment=hire_booking.payment,
            driver_profile=driver_profile,
            status='unverified',
            token_created_at=timezone.now() - timedelta(hours=1), # Token valid
            amount_to_refund=None, # Should be updated by view
            refund_calculation_details={} # Should be updated by view
        )

        # Construct the URL with the verification token
        url = reverse('payments:user_verify_refund') + f'?token={refund_request.verification_token}'
        
        # Make the GET request
        response = self.client.get(url)

        # Assertions
        self.assertEqual(response.status_code, 302) # Should redirect
        self.assertRedirects(response, reverse('payments:user_verified_refund'))

        # Reload the refund request from the database to check updated status
        refund_request.refresh_from_db()
        self.assertEqual(refund_request.status, 'pending')
        self.assertEqual(refund_request.amount_to_refund, Decimal('150.00'))
        self.assertIn('calculated_amount', refund_request.refund_calculation_details)
        self.assertEqual(refund_request.refund_calculation_details['calculated_amount'], 150.00)
        self.assertEqual(refund_request.refund_calculation_details['full_calculation_details']['details'], 'Hire refund calculated successfully.')

        # Check messages
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Your refund request has been successfully verified!")
        self.assertEqual(messages[0].tags, 'success')

        # Verify that calculate_hire_refund_amount was called
        mock_calculate_hire_refund.assert_called_once_with(
            booking=hire_booking,
            refund_policy_snapshot=hire_booking.payment.refund_policy_snapshot,
            cancellation_datetime=refund_request.requested_at
        )
        # Verify that calculate_service_refund_amount was NOT called
        mock_calculate_service_refund.assert_not_called()

        # Verify admin email was sent
        mock_send_templated_email.assert_called_once()
        call_args, call_kwargs = mock_send_templated_email.call_args
        self.assertIn('recipient_list', call_kwargs)
        self.assertIn('subject', call_kwargs)
        self.assertIn('VERIFIED Refund Request for Booking HIRE123', call_kwargs['subject'])
        self.assertIn('template_name', call_kwargs)
        self.assertEqual(call_kwargs['template_name'], 'admin_refund_request_notification.html')
        self.assertIn('context', call_kwargs)
        self.assertIn('admin_refund_link', call_kwargs['context'])
        self.assertIn(str(refund_request.pk), call_kwargs['context']['admin_refund_link'])
        self.assertEqual(call_kwargs['booking'], hire_booking)
        self.assertEqual(call_kwargs['driver_profile'], driver_profile)
        self.assertIsNone(call_kwargs.get('service_profile'))


    @patch('payments.views.Refunds.calculate_hire_refund_amount')
    @patch('payments.views.Refunds.calculate_service_refund_amount')
    @patch('payments.views.Refunds.send_templated_email')
    def test_successful_verification_service_booking(
        self, mock_send_templated_email, mock_calculate_service_refund, mock_calculate_hire_refund
    ):
        """
        Tests successful verification of a refund request for a ServiceBooking.
        Verifies status update, refund calculation, and admin email sending.
        """
        # Setup mock return values for refund calculation
        mock_calculate_service_refund.return_value = {
            'entitled_amount': Decimal('75.00'),
            'details': 'Service refund calculated successfully.',
            'policy_applied': 'Deposit Policy',
            'days_before_dropoff': 5
        }
        mock_calculate_hire_refund.return_value = {
            'entitled_amount': Decimal('0.00'),
            'details': 'No hire booking involved.',
            'policy_applied': 'N/A',
            'days_before_dropoff': 'N/A'
        }

        # Create a ServiceBooking and associated Payment and ServiceProfile
        service_booking = ServiceBookingFactory(
            payment=PaymentFactory(
                amount=Decimal('100.00'),
                status='deposit_paid',
                refund_policy_snapshot={'deposit_key': 'deposit_value'}
            ),
            dropoff_date=timezone.now().date() + timedelta(days=10),
            dropoff_time=time(9,0),
            service_booking_reference="SERVICE456"
        )
        service_profile = service_booking.service_profile # Get the one created by the booking factory

        # Create an unverified RefundRequest
        refund_request = RefundRequestFactory(
            hire_booking=None, # Ensure it's a service booking refund
            service_booking=service_booking,
            payment=service_booking.payment,
            service_profile=service_profile,
            status='unverified',
            token_created_at=timezone.now() - timedelta(hours=1), # Token valid
            amount_to_refund=None,
            refund_calculation_details={}
        )

        # Construct the URL with the verification token
        url = reverse('payments:user_verify_refund') + f'?token={refund_request.verification_token}'
        
        # Make the GET request
        response = self.client.get(url)

        # Assertions
        self.assertEqual(response.status_code, 302) # Should redirect
        self.assertRedirects(response, reverse('payments:user_verified_refund'))

        # Reload the refund request from the database to check updated status
        refund_request.refresh_from_db()
        self.assertEqual(refund_request.status, 'pending')
        self.assertEqual(refund_request.amount_to_refund, Decimal('75.00'))
        self.assertIn('calculated_amount', refund_request.refund_calculation_details)
        self.assertEqual(refund_request.refund_calculation_details['calculated_amount'], 75.00)
        self.assertEqual(refund_request.refund_calculation_details['full_calculation_details']['details'], 'Service refund calculated successfully.')


        # Check messages
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Your refund request has been successfully verified!")
        self.assertEqual(messages[0].tags, 'success')

        # Verify that calculate_service_refund_amount was called
        mock_calculate_service_refund.assert_called_once_with(
            booking=service_booking,
            refund_policy_snapshot=service_booking.payment.refund_policy_snapshot,
            cancellation_datetime=refund_request.requested_at
        )
        # Verify that calculate_hire_refund_amount was NOT called
        mock_calculate_hire_refund.assert_not_called()

        # Verify admin email was sent
        mock_send_templated_email.assert_called_once()
        call_args, call_kwargs = mock_send_templated_email.call_args
        self.assertIn('recipient_list', call_kwargs)
        self.assertIn('subject', call_kwargs)
        self.assertIn('VERIFIED Refund Request for Booking SERVICE456', call_kwargs['subject'])
        self.assertIn('template_name', call_kwargs)
        self.assertEqual(call_kwargs['template_name'], 'admin_refund_request_notification.html')
        self.assertIn('context', call_kwargs)
        self.assertIn('admin_refund_link', call_kwargs['context'])
        self.assertIn(str(refund_request.pk), call_kwargs['context']['admin_refund_link'])
        self.assertEqual(call_kwargs['booking'], service_booking)
        self.assertEqual(call_kwargs['service_profile'], service_profile)
        self.assertIsNone(call_kwargs.get('driver_profile'))

    def test_missing_token(self):
        """
        Tests behavior when no token is provided in the URL.
        """
        url = reverse('payments:user_verify_refund')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('core:index'))

        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Verification link is missing a token.")
        self.assertEqual(messages[0].tags, 'error')

    def test_invalid_token_format(self):
        """
        Tests behavior when an invalid UUID format is provided as a token.
        """
        url = reverse('payments:user_verify_refund') + '?token=invalid-uuid-string'
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('core:index'))

        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Invalid verification token format.")
        self.assertEqual(messages[0].tags, 'error')

    @patch('payments.views.Refunds.calculate_hire_refund_amount')
    @patch('payments.views.Refunds.calculate_service_refund_amount')
    @patch('payments.views.Refunds.send_templated_email')
    def test_non_existent_token(
        self, mock_send_templated_email, mock_calculate_service_refund, mock_calculate_hire_refund
    ):
        """
        Tests behavior when a valid UUID token is provided but it doesn't match any RefundRequest.
        """
        non_existent_token = uuid.uuid4()
        url = reverse('payments:user_verify_refund') + f'?token={non_existent_token}'
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('core:index'))

        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "The refund request associated with this token does not exist.")
        self.assertEqual(messages[0].tags, 'error')

        mock_calculate_hire_refund.assert_not_called()
        mock_calculate_service_refund.assert_not_called()
        mock_send_templated_email.assert_not_called()

    @patch('payments.views.Refunds.calculate_hire_refund_amount')
    @patch('payments.views.Refunds.calculate_service_refund_amount')
    @patch('payments.views.Refunds.send_templated_email')
    def test_expired_token(
        self, mock_send_templated_email, mock_calculate_service_refund, mock_calculate_hire_refund
    ):
        """
        Tests behavior when the verification token has expired.
        """
        # Create an unverified RefundRequest with an expired token
        # Using pickup_date and return_date for HireBooking
        refund_request = RefundRequestFactory(
            status='unverified',
            token_created_at=timezone.now() - timedelta(hours=25), # Token expired
            hire_booking=HireBookingFactory( # Link to a booking to make it a valid request otherwise
                pickup_date=timezone.now().date() + timedelta(days=1),
                pickup_time=time(10,0),
                return_date=timezone.now().date() + timedelta(days=2)
            )
        )

        url = reverse('payments:user_verify_refund') + f'?token={refund_request.verification_token}'
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('payments:user_refund_request'))

        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "The verification link has expired. Please submit a new refund request.")
        self.assertEqual(messages[0].tags, 'error')

        # Ensure refund request status is NOT changed
        refund_request.refresh_from_db()
        self.assertEqual(refund_request.status, 'unverified')

        mock_calculate_hire_refund.assert_not_called()
        mock_calculate_service_refund.assert_not_called()
        mock_send_templated_email.assert_not_called()

    @patch('payments.views.Refunds.calculate_hire_refund_amount')
    @patch('payments.views.Refunds.calculate_service_refund_amount')
    @patch('payments.views.Refunds.send_templated_email')
    def test_already_verified_token(
        self, mock_send_templated_email, mock_calculate_service_refund, mock_calculate_hire_refund
    ):
        """
        Tests behavior when the refund request has already been verified (status is not 'unverified').
        """
        # Create a RefundRequest that is already in 'pending' status
        # Using pickup_date and return_date for HireBooking
        refund_request = RefundRequestFactory(
            status='pending', # Already verified or processed
            token_created_at=timezone.now() - timedelta(hours=1), # Token is technically valid
            hire_booking=HireBookingFactory(
                pickup_date=timezone.now().date() + timedelta(days=1),
                pickup_time=time(10,0),
                return_date=timezone.now().date() + timedelta(days=2)
            )
        )

        url = reverse('payments:user_verify_refund') + f'?token={refund_request.verification_token}'
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('payments:user_verified_refund'))

        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "This refund request has already been verified or processed.")
        self.assertEqual(messages[0].tags, 'info')

        # Ensure refund request status is NOT changed
        refund_request.refresh_from_db()
        self.assertEqual(refund_request.status, 'pending')

        mock_calculate_hire_refund.assert_not_called()
        mock_calculate_service_refund.assert_not_called()
        mock_send_templated_email.assert_not_called()

    @patch('payments.views.Refunds.calculate_hire_refund_amount')
    @patch('payments.views.Refunds.calculate_service_refund_amount')
    @patch('payments.views.Refunds.send_templated_email')
    def test_exception_during_calculation(
        self, mock_send_templated_email, mock_calculate_service_refund, mock_calculate_hire_refund
    ):
        """
        Tests behavior when an exception occurs during refund calculation.
        """
        # Create a mock for calculate_hire_refund_amount that raises an exception
        mock_calculate_hire_refund.side_effect = Exception("Calculation error")

        hire_booking = HireBookingFactory(
            payment=PaymentFactory(refund_policy_snapshot={'key': 'value'}),
            pickup_date=timezone.now().date() + timedelta(days=5),
            pickup_time=time(10,0),
            return_date=timezone.now().date() + timedelta(days=15)
        )
        refund_request = RefundRequestFactory(
            hire_booking=hire_booking,
            service_booking=None,
            payment=hire_booking.payment,
            status='unverified',
            token_created_at=timezone.now() - timedelta(hours=1)
        )

        url = reverse('payments:user_verify_refund') + f'?token={refund_request.verification_token}'
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('core:index')) # This is the expected redirect on exception

        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertIn("An unexpected error occurred during verification:", str(messages[0]))
        self.assertEqual(messages[0].tags, 'error')

        # Ensure status is not updated if an error occurs mid-process
        refund_request.refresh_from_db()
        # The status should remain 'unverified' if an error occurs *before* final success
        # The view updates the status to 'pending' before calculation, so it should be 'pending' if it gets there.
        # Let's adjust this expectation: if an exception happens AFTER the status update, the status should be pending.
        # But if the exception happens *before* the save, it would remain unverified.
        # Looking at the view, `refund_request.status = 'pending'` happens *before* the calculation.
        # So, if calculation fails, it should be 'pending'.
        self.assertEqual(refund_request.status, 'pending')

        mock_calculate_hire_refund.assert_called_once()
        mock_send_templated_email.assert_not_called() # Email should not be sent on failure

    @patch('payments.views.Refunds.calculate_hire_refund_amount')
    @patch('payments.views.Refunds.calculate_service_refund_amount')
    @patch('payments.views.Refunds.send_templated_email')
    def test_exception_during_email_sending(
        self, mock_send_templated_email, mock_calculate_service_refund, mock_calculate_hire_refund
    ):
        """
        Tests behavior when an exception occurs during admin email sending,
        after the refund request status and calculation details have been updated.
        The status change and calculation should persist.
        """
        mock_calculate_hire_refund.return_value = {
            'entitled_amount': Decimal('100.00'),
            'details': 'Calculated',
            'policy_applied': 'Test',
            'days_before_dropoff': 5
        }
        # Create a mock for send_templated_email that raises an exception
        mock_send_templated_email.side_effect = Exception("Email sending error")


        hire_booking = HireBookingFactory(
            payment=PaymentFactory(refund_policy_snapshot={'key': 'value'}),
            pickup_date=timezone.now().date() + timedelta(days=5),
            pickup_time=time(10,0),
            return_date=timezone.now().date() + timedelta(days=15)
        )
        refund_request = RefundRequestFactory(
            hire_booking=hire_booking,
            service_booking=None,
            payment=hire_booking.payment,
            status='unverified',
            token_created_at=timezone.now() - timedelta(hours=1)
        )

        url = reverse('payments:user_verify_refund') + f'?token={refund_request.verification_token}'
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('core:index')) # This is the expected redirect on exception

        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertIn("An unexpected error occurred during verification:", str(messages[0]))
        self.assertEqual(messages[0].tags, 'error')

        # Crucially, the refund request status and calculation details should still be updated
        refund_request.refresh_from_db()
        self.assertEqual(refund_request.status, 'pending')
        self.assertEqual(refund_request.amount_to_refund, Decimal('100.00'))
        self.assertIn('calculated_amount', refund_request.refund_calculation_details)
        self.assertEqual(refund_request.refund_calculation_details['calculated_amount'], 100.00)

        mock_calculate_hire_refund.assert_called_once()
        mock_send_templated_email.assert_called_once() # Should have attempted to send email


    @patch('payments.views.Refunds.calculate_hire_refund_amount')
    @patch('payments.views.Refunds.calculate_service_refund_amount')
    @patch('payments.views.Refunds.send_templated_email')
    def test_refund_request_with_no_linked_payment(
        self, mock_send_templated_email, mock_calculate_service_refund, mock_calculate_hire_refund
    ):
        """
        Tests verification for a refund request that has no linked payment object.
        Refund amount should be 0.00 and calculation details should reflect 'No calculation performed.'.
        """
        mock_calculate_hire_refund.return_value = {
            'entitled_amount': Decimal('0.00'),
            'details': 'No calculation performed.',
            'policy_applied': 'N/A',
            'days_before_dropoff': 'N/A'
        }
        mock_calculate_service_refund.return_value = {
            'entitled_amount': Decimal('0.00'),
            'details': 'No calculation performed.',
            'policy_applied': 'N/A',
            'days_before_dropoff': 'N/A'
        }

        # Using pickup_date and return_date for HireBooking
        hire_booking = HireBookingFactory(
            payment=None, # No linked payment
            pickup_date=timezone.now().date() + timedelta(days=5),
            pickup_time=time(10,0),
            return_date=timezone.now().date() + timedelta(days=15)
        )
        refund_request = RefundRequestFactory(
            hire_booking=hire_booking,
            service_booking=None,
            payment=None, # Explicitly no payment
            status='unverified',
            token_created_at=timezone.now() - timedelta(hours=1)
        )

        url = reverse('payments:user_verify_refund') + f'?token={refund_request.verification_token}'
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('payments:user_verified_refund'))

        refund_request.refresh_from_db()
        self.assertEqual(refund_request.status, 'pending')
        self.assertEqual(refund_request.amount_to_refund, Decimal('0.00')) # Should be 0.00
        self.assertIn('calculated_amount', refund_request.refund_calculation_details)
        self.assertEqual(refund_request.refund_calculation_details['calculated_amount'], 0.00)
        self.assertEqual(refund_request.refund_calculation_details['full_calculation_details']['details'], 'No calculation performed.')

        # calculate_hire_refund_amount should still be called, but with an empty snapshot
        mock_calculate_hire_refund.assert_called_once_with(
            booking=hire_booking,
            refund_policy_snapshot={}, # Empty snapshot
            cancellation_datetime=refund_request.requested_at
        )
        mock_calculate_service_refund.assert_not_called()
        mock_send_templated_email.assert_called_once()

    @patch('payments.views.Refunds.calculate_hire_refund_amount')
    @patch('payments.views.Refunds.calculate_service_refund_amount')
    @patch('payments.views.Refunds.send_templated_email')
    def test_refund_request_with_payment_but_no_snapshot(
        self, mock_send_templated_email, mock_calculate_service_refund, mock_calculate_hire_refund
    ):
        """
        Tests verification for a refund request where the Payment object exists,
        but its refund_policy_snapshot is None or empty.
        Calculation utility should receive an empty dict for the snapshot.
        """
        mock_calculate_hire_refund.return_value = {
            'entitled_amount': Decimal('0.00'),
            'details': 'No refund policy snapshot available for this booking.',
            'policy_applied': 'N/A',
            'days_before_dropoff': 'N/A'
        }
        mock_calculate_service_refund.return_value = {
            'entitled_amount': Decimal('0.00'),
            'details': 'No refund policy snapshot available for this booking.',
            'policy_applied': 'N/A',
            'days_before_dropoff': 'N/A'
        }

        payment = PaymentFactory(
            refund_policy_snapshot=None # Explicitly set to None
        )
        # Using pickup_date and return_date for HireBooking
        hire_booking = HireBookingFactory(
            payment=payment,
            pickup_date=timezone.now().date() + timedelta(days=5),
            pickup_time=time(10,0),
            return_date=timezone.now().date() + timedelta(days=15)
        )
        refund_request = RefundRequestFactory(
            hire_booking=hire_booking,
            service_booking=None,
            payment=payment,
            status='unverified',
            token_created_at=timezone.now() - timedelta(hours=1)
        )

        url = reverse('payments:user_verify_refund') + f'?token={refund_request.verification_token}'
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('payments:user_verified_refund'))

        refund_request.refresh_from_db()
        self.assertEqual(refund_request.status, 'pending')
        self.assertEqual(refund_request.amount_to_refund, Decimal('0.00'))
        self.assertIn('calculated_amount', refund_request.refund_calculation_details)
        self.assertEqual(refund_request.refund_calculation_details['calculated_amount'], 0.00)
        self.assertEqual(refund_request.refund_calculation_details['full_calculation_details']['details'], 'No refund policy snapshot available for this booking.')

        mock_calculate_hire_refund.assert_called_once_with(
            booking=hire_booking,
            refund_policy_snapshot={}, # Should be empty dict
            cancellation_datetime=refund_request.requested_at
        )
        mock_calculate_service_refund.assert_not_called()
        mock_send_templated_email.assert_called_once()

    @patch('payments.views.Refunds.calculate_hire_refund_amount')
    @patch('payments.views.Refunds.calculate_service_refund_amount')
    @patch('payments.views.Refunds.send_templated_email')
    def test_refund_request_with_no_booking_linked(
        self, mock_send_templated_email, mock_calculate_service_refund, mock_calculate_hire_refund
    ):
        """
        Tests verification for a refund request that has no linked hire_booking or service_booking.
        This case should result in no calculation and a 0.00 amount.
        """
        mock_calculate_hire_refund.return_value = {
            'entitled_amount': Decimal('0.00'),
            'details': 'No calculation performed.',
            'policy_applied': 'N/A',
            'days_before_dropoff': 'N/A'
        }
        mock_calculate_service_refund.return_value = {
            'entitled_amount': Decimal('0.00'),
            'details': 'No calculation performed.',
            'policy_applied': 'N/A',
            'days_before_dropoff': 'N/A'
        }

        # Create a refund request with no linked booking but a payment
        refund_request = RefundRequestFactory(
            hire_booking=None,
            service_booking=None,
            payment=PaymentFactory(refund_policy_snapshot={'key': 'value'}),
            status='unverified',
            token_created_at=timezone.now() - timedelta(hours=1)
        )

        url = reverse('payments:user_verify_refund') + f'?token={refund_request.verification_token}'
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('payments:user_verified_refund'))

        refund_request.refresh_from_db()
        self.assertEqual(refund_request.status, 'pending')
        self.assertEqual(refund_request.amount_to_refund, Decimal('0.00')) # Should be 0.00
        self.assertIn('calculated_amount', refund_request.refund_calculation_details)
        self.assertEqual(refund_request.refund_calculation_details['calculated_amount'], 0.00)
        self.assertEqual(refund_request.refund_calculation_details['full_calculation_details']['details'], 'No calculation performed.')


        mock_calculate_hire_refund.assert_not_called() # No booking, so no calculation specific to booking type
        mock_calculate_service_refund.assert_not_called()
        mock_send_templated_email.assert_called_once()
