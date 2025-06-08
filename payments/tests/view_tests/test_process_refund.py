# payments/tests/view_tests/test_process_refund_view.py

from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from unittest import mock
from decimal import Decimal
from django.contrib import messages
from django.contrib.messages.storage.base import Message # Import Message for checking messages

# Import the view to be tested
from payments.views.Refunds.process_refund import ProcessRefundView

# Import models
from payments.models import RefundRequest, Payment
from hire.models import HireBooking, DriverProfile

# Import actual StripeError for mocking
import stripe.error

# Import model factories for creating test data
from hire.tests.test_helpers.model_factories import (
    create_user,
    create_hire_booking,
    create_payment,
    create_driver_profile,
    create_refund_request,
    create_hire_settings,
)

# Mock Stripe for testing purposes
STRIPE_REFUND_CREATE_PATH = 'payments.views.HireRefunds.process_refund.stripe.Refund.create'

@override_settings(STRIPE_SECRET_KEY='sk_test_mock_key', LOGIN_URL='/accounts/login/') # Mock Stripe secret key and set LOGIN_URL
class ProcessRefundViewTests(TestCase):
    """
    Tests for the ProcessRefundView, which handles initiating Stripe refunds.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up common test data for all tests, run once for the class.
        """
        cls.staff_user = create_user(username='adminuser', email='admin@example.com', is_staff=True)
        cls.regular_user = create_user(username='regularuser', email='user@example.com', is_staff=False)

        # Ensure HireSettings exists
        cls.hire_settings = create_hire_settings()

        # Create a driver profile
        cls.driver_profile = create_driver_profile(user=cls.regular_user, email='test@example.com')

        # Create a base payment that has a Stripe Payment Intent ID
        cls.payment = create_payment(
            amount=Decimal('500.00'),
            status='succeeded',
            driver_profile=cls.driver_profile,
            stripe_payment_intent_id='pi_mock_12345', # Crucial for Stripe refund
            refund_policy_snapshot={}
        )
        # Create a base hire booking linked to the payment
        cls.hire_booking = create_hire_booking(
            driver_profile=cls.driver_profile,
            payment=cls.payment,
            amount_paid=cls.payment.amount,
            grand_total=cls.payment.amount,
            payment_status='paid',
            status='confirmed',
        )
        cls.payment.hire_booking = cls.hire_booking
        cls.payment.save()

        # Create a hire booking with no payment for specific test case
        cls.hire_booking_no_payment = create_hire_booking(
            driver_profile=cls.driver_profile,
            payment=None, # Explicitly no payment
            amount_paid=Decimal('0.00'),
            grand_total=Decimal('200.00'),
            payment_status='unpaid',
            status='pending',
        )

    def setUp(self):
        """
        Set up for each individual test method.
        """
        self.client = Client()
        # URL for processing refunds
        self.process_url = lambda pk: reverse('dashboard:process_hire_refund', kwargs={'pk': pk})
        self.management_url = reverse('payments:admin_refund_management')

    def _login_staff_user(self):
        """Helper to log in the staff user."""
        self.client.login(username=self.staff_user.username, password='password123')

    @mock.patch(STRIPE_REFUND_CREATE_PATH)
    def test_successful_refund_initiation(self, mock_stripe_refund_create):
        """
        Test that a refund is successfully initiated via Stripe API
        and the RefundRequest status is updated.
        """
        # Mock Stripe's response for a successful refund creation
        mock_stripe_refund_create.return_value = mock.Mock(id='re_mock_123', status='succeeded')

        # Create a refund request ready for processing
        refund_request = create_refund_request(
            hire_booking=self.hire_booking,
            payment=self.payment,
            driver_profile=self.driver_profile,
            status='reviewed_pending_approval', # Or 'approved'
            amount_to_refund=Decimal('100.00'),
            reason="Customer requested refund"
        )

        self._login_staff_user()

        response = self.client.post(self.process_url(refund_request.pk))

        # Assert redirect to management page
        self.assertRedirects(response, self.management_url)

        # Assert Stripe API was called correctly
        mock_stripe_refund_create.assert_called_once_with(
            payment_intent=self.payment.stripe_payment_intent_id,
            amount=10000, # 100.00 * 100 cents
            reason='requested_by_customer',
            metadata={
                'hire_refund_request_id': str(refund_request.pk),
                'admin_user_id': str(self.staff_user.pk),
                'booking_reference': self.hire_booking.booking_reference,
            }
        )

        # Reload the refund request from DB to check updated status
        refund_request.refresh_from_db()
        self.assertEqual(refund_request.status, 'approved') # Status updated immediately
        self.assertEqual(refund_request.processed_by, self.staff_user)
        self.assertIsNotNone(refund_request.processed_at)

        # Check for success message
        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 1)
        self.assertEqual(str(messages_list[0]), f"Refund for booking '{self.hire_booking.booking_reference}' initiated successfully with Stripe (ID: re_mock_123). Status updated to 'Approved - Awaiting Refund'.")
        self.assertEqual(messages_list[0].tags, 'success')


    @mock.patch(STRIPE_REFUND_CREATE_PATH)
    def test_refund_initiation_with_approved_status(self, mock_stripe_refund_create):
        """
        Test that a refund is successfully initiated when the status is 'approved'.
        """
        mock_stripe_refund_create.return_value = mock.Mock(id='re_mock_approved', status='succeeded')

        refund_request = create_refund_request(
            hire_booking=self.hire_booking,
            payment=self.payment,
            driver_profile=self.driver_profile,
            status='approved', # Test 'approved' status
            amount_to_refund=Decimal('50.00'),
            reason="Approved refund"
        )

        self._login_staff_user()
        response = self.client.post(self.process_url(refund_request.pk))

        self.assertRedirects(response, self.management_url)
        mock_stripe_refund_create.assert_called_once()
        refund_request.refresh_from_db()
        self.assertEqual(refund_request.status, 'approved') # Stays 'approved' or moves to 'approved_awaiting_stripe' if you change it


    @mock.patch(STRIPE_REFUND_CREATE_PATH)
    def test_refund_initiation_invalid_status(self, mock_stripe_refund_create):
        """
        Test that a refund is NOT initiated if the request status is not 'approved'
        or 'reviewed_pending_approval'.
        """
        refund_request = create_refund_request(
            hire_booking=self.hire_booking,
            payment=self.payment,
            driver_profile=self.driver_profile,
            status='pending', # Invalid status for processing
            amount_to_refund=Decimal('100.00')
        )

        self._login_staff_user() # Log in staff user so the decorator passes

        response = self.client.post(self.process_url(refund_request.pk))

        # Assert redirect back to management page (this is the expected behavior from the view's logic)
        self.assertRedirects(response, self.management_url)

        # Assert Stripe API was NOT called
        mock_stripe_refund_create.assert_not_called()

        # Assert status remains unchanged
        refund_request.refresh_from_db()
        self.assertEqual(refund_request.status, 'pending')

        # Check for error message
        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 1)
        # FIX: Corrected expected message string to include the trailing period
        self.assertEqual(str(messages_list[0]), "Refund request is not in an approvable state. Current status: Pending Review.")
        self.assertEqual(messages_list[0].tags, 'error')

    @mock.patch(STRIPE_REFUND_CREATE_PATH)
    def test_refund_initiation_no_associated_payment(self, mock_stripe_refund_create):
        """
        Test that a refund is NOT initiated if there's no associated payment.
        """
        # FIX: Create a refund request linked to a booking that has no payment
        refund_request = create_refund_request(
            hire_booking=self.hire_booking_no_payment, # Use the booking without a payment
            payment=None, # Explicitly pass None, the factory won't override if booking.payment is None
            driver_profile=self.driver_profile,
            status='approved',
            amount_to_refund=Decimal('100.00')
        )

        self._login_staff_user()
        response = self.client.post(self.process_url(refund_request.pk))

        self.assertRedirects(response, self.management_url)
        mock_stripe_refund_create.assert_not_called()

        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 1)
        self.assertEqual(str(messages_list[0]), "Cannot process refund: No associated payment found for this request.")
        self.assertEqual(messages_list[0].tags, 'error')

    @mock.patch(STRIPE_REFUND_CREATE_PATH)
    def test_refund_initiation_no_amount_to_refund(self, mock_stripe_refund_create):
        """
        Test that a refund is NOT initiated if amount_to_refund is None or 0.
        """
        # FIX: Explicitly set amount_to_refund to 0.00 in the factory call
        refund_request = create_refund_request(
            hire_booking=self.hire_booking,
            payment=self.payment,
            driver_profile=self.driver_profile,
            status='approved',
            amount_to_refund=Decimal('0.00') # Explicitly set to 0.00
        )

        self._login_staff_user()
        response = self.client.post(self.process_url(refund_request.pk))

        self.assertRedirects(response, self.management_url)
        mock_stripe_refund_create.assert_not_called() # Should not be called

        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 1)
        # FIX: Updated message to match the view's new message
        self.assertEqual(str(messages_list[0]), "Cannot process refund: No valid amount specified to refund.")
        self.assertEqual(messages_list[0].tags, 'error')

    @mock.patch(STRIPE_REFUND_CREATE_PATH)
    def test_refund_initiation_no_stripe_payment_intent_id(self, mock_stripe_refund_create):
        """
        Test that a refund is NOT initiated if the associated payment has no Stripe Payment Intent ID.
        """
        payment_no_stripe_id = create_payment(
            amount=Decimal('500.00'),
            status='succeeded',
            driver_profile=self.driver_profile,
            stripe_payment_intent_id=None, # Missing Stripe ID
            refund_policy_snapshot={}
        )
        hire_booking_no_stripe_id = create_hire_booking(
            driver_profile=self.driver_profile,
            payment=payment_no_stripe_id,
            amount_paid=payment_no_stripe_id.amount,
            grand_total=payment_no_stripe_id.amount,
            payment_status='paid',
            status='confirmed',
        )
        payment_no_stripe_id.hire_booking = hire_booking_no_stripe_id
        payment_no_stripe_id.save()


        refund_request = create_refund_request(
            hire_booking=hire_booking_no_stripe_id,
            payment=payment_no_stripe_id,
            driver_profile=self.driver_profile,
            status='approved',
            amount_to_refund=Decimal('100.00')
        )

        self._login_staff_user()
        response = self.client.post(self.process_url(refund_request.pk))

        self.assertRedirects(response, self.management_url)
        mock_stripe_refund_create.assert_not_called()

        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 1)
        self.assertEqual(str(messages_list[0]), "Cannot process refund: Associated payment has no Stripe Payment Intent ID.")
        self.assertEqual(messages_list[0].tags, 'error')


    @mock.patch(STRIPE_REFUND_CREATE_PATH)
    def test_stripe_api_error_handling(self, mock_stripe_refund_create):
        """
        Test that Stripe API errors are caught, a message is displayed,
        and the refund request status is updated to 'failed'.
        """
        # FIX: Correctly mock StripeError by raising an instance of it, removing 'param'
        mock_stripe_refund_create.side_effect = stripe.error.StripeError(
            message='Stripe API error message',
            http_body='{}',
            http_status=400,
            json_body={},
            headers={},
            code='some_code', # 'code' is a valid argument for StripeError
        )

        refund_request = create_refund_request(
            hire_booking=self.hire_booking,
            payment=self.payment,
            driver_profile=self.driver_profile,
            status='approved',
            amount_to_refund=Decimal('100.00')
        )

        self._login_staff_user()
        response = self.client.post(self.process_url(refund_request.pk))

        self.assertRedirects(response, self.management_url)

        # Assert Stripe API was called
        mock_stripe_refund_create.assert_called_once()

        # Reload the refund request from DB to check updated status
        refund_request.refresh_from_db()
        self.assertEqual(refund_request.status, 'failed')
        self.assertIn("Stripe initiation failed", refund_request.staff_notes)

        # Check for error message
        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 1)
        self.assertEqual(str(messages_list[0]), "Stripe error initiating refund: Stripe API error message")
        self.assertEqual(messages_list[0].tags, 'error')

    @mock.patch(STRIPE_REFUND_CREATE_PATH)
    def test_unexpected_error_handling(self, mock_stripe_refund_create):
        """
        Test that unexpected Python errors are caught, a message is displayed,
        and the refund request status is updated to 'failed'.
        """
        # Mock Stripe to raise a generic Python Exception
        mock_stripe_refund_create.side_effect = Exception("Something went wrong unexpectedly!")

        refund_request = create_refund_request(
            hire_booking=self.hire_booking,
            payment=self.payment,
            driver_profile=self.driver_profile,
            status='approved',
            amount_to_refund=Decimal('100.00')
        )

        self._login_staff_user()
        response = self.client.post(self.process_url(refund_request.pk))

        self.assertRedirects(response, self.management_url)

        # Assert Stripe API was called
        mock_stripe_refund_create.assert_called_once()

        # Reload the refund request from DB to check updated status
        refund_request.refresh_from_db()
        self.assertEqual(refund_request.status, 'failed')
        self.assertIn("Unexpected error during initiation", refund_request.staff_notes)

        # Check for error message
        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 1)
        self.assertEqual(str(messages_list[0]), "An unexpected error occurred: Something went wrong unexpectedly!")
        self.assertEqual(messages_list[0].tags, 'error')

    def test_unauthenticated_user_redirected(self):
        """
        Test that an unauthenticated user is redirected to the login page.
        """
        refund_request = create_refund_request(
            hire_booking=self.hire_booking,
            payment=self.payment,
            driver_profile=self.driver_profile,
            status='approved',
            amount_to_refund=Decimal('100.00')
        )
        response = self.client.post(self.process_url(refund_request.pk))
        # Expected redirect URL is now /accounts/login/
        self.assertRedirects(response, f'/accounts/login/?next={self.process_url(refund_request.pk)}')

    def test_non_staff_user_redirected(self):
        """
        Test that a non-staff authenticated user is redirected to the login page.
        """
        refund_request = create_refund_request(
            hire_booking=self.hire_booking,
            payment=self.payment,
            driver_profile=self.driver_profile,
            status='approved',
            amount_to_refund=Decimal('100.00')
        )
        self.client.login(username=self.regular_user.username, password='password123')
        response = self.client.post(self.process_url(refund_request.pk))
        # Expected redirect URL is now /accounts/login/
        self.assertRedirects(response, f'/accounts/login/?next={self.process_url(refund_request.pk)}')

    def test_get_request_not_allowed(self):
        """
        Test that GET requests to the process refund URL are not allowed
        when accessed by an authenticated staff user.
        """
        refund_request = create_refund_request(
            hire_booking=self.hire_booking,
            payment=self.payment,
            driver_profile=self.driver_profile,
            status='approved',
            amount_to_refund=Decimal('100.00')
        )
        self._login_staff_user() # Log in the staff user
        response = self.client.get(self.process_url(refund_request.pk))
        # Now that the user is logged in and staff, the decorator passes,
        # and the View's dispatch method correctly returns 405 for GET.
        self.assertEqual(response.status_code, 405) # Method Not Allowed
