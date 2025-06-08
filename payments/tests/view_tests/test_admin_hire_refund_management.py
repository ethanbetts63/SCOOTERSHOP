# payments/tests/view_tests/test_admin_hire_refund_management.py

from django.test import TestCase, Client, override_settings # Import override_settings
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from unittest import mock
from decimal import Decimal

# Import the view to be tested
from payments.views.HireRefunds.admin_hire_refund_management import AdminHireRefundManagement

# Import models
from payments.models.RefundRequest import RefundRequest
from mailer.models import EmailLog

# Import model factories for creating test data
from hire.tests.test_helpers.model_factories import (
    create_user,
    create_hire_booking,
    create_payment,
    create_driver_profile,
    create_refund_request,
    create_hire_settings,
    create_email_log,
)

@override_settings(DEFAULT_FROM_EMAIL='test@scootershop.com') # Apply settings override at class level
class AdminHireRefundManagementTests(TestCase):
    """
    Tests for the AdminHireRefundManagement ListView, including the cleaning mechanism.
    """

    def setUp(self):
        """
        Set up common test data for all tests.
        """
        self.client = Client()
        self.staff_user = create_user(username='adminuser', email='admin@example.com', is_staff=True)
        self.regular_user = create_user(username='regularuser', email='user@example.com', is_staff=False)

        # Ensure HireSettings exists as it's used in payment/refund_request creation
        self.hire_settings = create_hire_settings()

        # Create a driver profile with an email for general tests
        self.driver_profile = create_driver_profile(user=self.regular_user, email='test@example.com')

        # Create a base booking and payment for refund requests
        self.payment = create_payment(
            amount=Decimal('500.00'),
            status='succeeded',
            driver_profile=self.driver_profile,
            refund_policy_snapshot={} # Empty for simplicity in this test
        )
        self.hire_booking = create_hire_booking(
            driver_profile=self.driver_profile,
            payment=self.payment,
            amount_paid=self.payment.amount,
            grand_total=self.payment.amount,
            payment_status='paid',
            status='confirmed',
        )
        self.payment.hire_booking = self.hire_booking
        self.payment.save()

        self.management_url = reverse('dashboard:admin_hire_refund_management')

    # No tearDown needed for settings override when using @override_settings decorator

    def _login_staff_user(self):
        """Helper to log in the staff user."""
        self.client.login(username=self.staff_user.username, password='password123')

    # Corrected mock path to target where send_templated_email is imported in the view
    @mock.patch('payments.views.HireRefunds.admin_hire_refund_management.send_templated_email')
    def test_expired_unverified_requests_are_cleaned_and_email_sent(self, mock_send_templated_email):
        """
        Test that 'unverified' refund requests older than 24 hours are deleted
        and an email notification is sent to the user.
        """
        # Create an expired unverified refund request (older than 24 hours)
        expired_request = create_refund_request(
            hire_booking=self.hire_booking,
            payment=self.payment,
            driver_profile=self.driver_profile,
            status='unverified',
            token_created_at=timezone.now() - timedelta(hours=24, minutes=1), # Just over 24 hours
            request_email='expired_user@example.com' # Specific email for this request
        )

        # Create a non-expired unverified request (within 24 hours)
        non_expired_request = create_refund_request(
            hire_booking=self.hire_booking,
            payment=self.payment,
            driver_profile=self.driver_profile,
            status='unverified',
            token_created_at=timezone.now() - timedelta(hours=23), # Within 24 hours
            request_email='non_expired_user@example.com'
        )

        # Create a pending request (should not be affected)
        pending_request = create_refund_request(
            hire_booking=self.hire_booking,
            payment=self.payment,
            driver_profile=self.driver_profile,
            status='pending',
            request_email='pending_user@example.com'
        )

        initial_count = RefundRequest.objects.count()
        self._login_staff_user()

        # Access the page, which triggers the cleaning mechanism in get_queryset
        response = self.client.get(self.management_url)

        self.assertEqual(response.status_code, 200)

        # Assert that only the expired request was deleted
        self.assertEqual(RefundRequest.objects.count(), initial_count - 1)
        self.assertFalse(RefundRequest.objects.filter(pk=expired_request.pk).exists())
        self.assertTrue(RefundRequest.objects.filter(pk=non_expired_request.pk).exists())
        self.assertTrue(RefundRequest.objects.filter(pk=pending_request.pk).exists())

        # Assert that send_templated_email was called exactly once for the expired request
        mock_send_templated_email.assert_called_once()
        call_args, call_kwargs = mock_send_templated_email.call_args
        self.assertIn('recipient_list', call_kwargs)
        self.assertEqual(call_kwargs['recipient_list'], ['expired_user@example.com'])
        self.assertIn('subject', call_kwargs)
        self.assertIn("Has Expired", call_kwargs['subject'])
        self.assertEqual(call_kwargs['template_name'], 'emails/user_refund_request_expired_unverified.html')
        # Compare UUIDs as strings
        # Compare the verification_token to ensure the correct request was processed
        self.assertEqual(call_kwargs['context']['refund_request'].verification_token, expired_request.verification_token)

    # Corrected mock path
    @mock.patch('payments.views.HireRefunds.admin_hire_refund_management.send_templated_email')
    def test_no_expired_unverified_requests_no_cleaning_or_email(self, mock_send_templated_email):
        """
        Test that if there are no expired 'unverified' requests, no cleaning occurs
        and no expiration emails are sent.
        """
        # Create a non-expired unverified request
        non_expired_request = create_refund_request(
            hire_booking=self.hire_booking,
            payment=self.payment,
            driver_profile=self.driver_profile,
            status='unverified',
            token_created_at=timezone.now() - timedelta(hours=1), # Within 24 hours
            request_email='non_expired_user@example.com'
        )

        # Create a pending request
        pending_request = create_refund_request(
            hire_booking=self.hire_booking,
            payment=self.payment,
            driver_profile=self.driver_profile,
            status='pending',
            request_email='pending_user@example.com'
        )

        initial_count = RefundRequest.objects.count()
        self._login_staff_user()

        # Access the page
        response = self.client.get(self.management_url)

        self.assertEqual(response.status_code, 200)

        # Assert no requests were deleted
        self.assertEqual(RefundRequest.objects.count(), initial_count)
        self.assertTrue(RefundRequest.objects.filter(pk=non_expired_request.pk).exists())
        self.assertTrue(RefundRequest.objects.filter(pk=pending_request.pk).exists())

        # Assert that send_templated_email was NOT called
        mock_send_templated_email.assert_not_called()

    # Corrected mock path
    @mock.patch('payments.views.HireRefunds.admin_hire_refund_management.send_templated_email')
    def test_cleaning_mechanism_handles_missing_email(self, mock_send_templated_email):
        """
        Test that the cleaning mechanism still deletes requests even if an email cannot be sent
        (e.g., missing request_email and driver_profile.user.email).
        """
        # Create a driver profile with no email (empty string)
        driver_profile_no_email = create_driver_profile(user=None, email='')

        # Create an expired unverified request with no email info
        expired_request_no_email = create_refund_request(
            hire_booking=self.hire_booking,
            payment=self.payment,
            driver_profile=driver_profile_no_email, # Link to driver with no email
            status='unverified',
            token_created_at=timezone.now() - timedelta(hours=25),
            request_email=None # Explicitly set request_email to None
        )

        initial_count = RefundRequest.objects.count()
        self._login_staff_user()

        response = self.client.get(self.management_url)

        self.assertEqual(response.status_code, 200)

        # Assert the request was still deleted
        self.assertEqual(RefundRequest.objects.count(), initial_count - 1)
        self.assertFalse(RefundRequest.objects.filter(pk=expired_request_no_email.pk).exists())

        # Assert that send_templated_email was NOT called for this specific case
        mock_send_templated_email.assert_not_called() # It should not be called if no recipient_email is found

    def test_get_queryset_filtering_after_cleaning(self):
        """
        Test that the get_queryset still filters correctly after the cleaning process.
        """
        # Create an expired unverified request that will be cleaned
        create_refund_request(
            hire_booking=self.hire_booking,
            payment=self.payment,
            driver_profile=self.driver_profile,
            status='unverified',
            token_created_at=timezone.now() - timedelta(hours=25),
            request_email='temp@example.com'
        )

        # Create requests with various statuses that should remain
        pending_req1 = create_refund_request(
            hire_booking=self.hire_booking,
            payment=self.payment,
            driver_profile=self.driver_profile,
            status='pending',
            reason="Pending review 1"
        )
        approved_req1 = create_refund_request(
            hire_booking=self.hire_booking,
            payment=self.payment,
            driver_profile=self.driver_profile,
            status='approved',
            reason="Approved refund 1"
        )
        non_expired_unverified = create_refund_request(
            hire_booking=self.hire_booking,
            payment=self.payment,
            driver_profile=self.driver_profile,
            status='unverified',
            token_created_at=timezone.now() - timedelta(hours=1), # Not expired
            reason="Unverified not expired"
        )

        self._login_staff_user()

        # Test filtering for 'pending' status
        response_pending = self.client.get(f"{self.management_url}?status=pending")
        self.assertEqual(response_pending.status_code, 200)
        self.assertIn(pending_req1, response_pending.context['refund_requests'])
        self.assertNotIn(approved_req1, response_pending.context['refund_requests'])
        self.assertNotIn(non_expired_unverified, response_pending.context['refund_requests'])
        self.assertEqual(len(response_pending.context['refund_requests']), 1)

        # Test filtering for 'unverified' status
        response_unverified = self.client.get(f"{self.management_url}?status=unverified")
        self.assertEqual(response_unverified.status_code, 200)
        self.assertIn(non_expired_unverified, response_unverified.context['refund_requests'])
        self.assertNotIn(pending_req1, response_unverified.context['refund_requests'])
        self.assertNotIn(approved_req1, response_unverified.context['refund_requests'])
        self.assertEqual(len(response_unverified.context['refund_requests']), 1)

        # Test filtering for 'all' statuses
        response_all = self.client.get(f"{self.management_url}?status=all")
        self.assertEqual(response_all.status_code, 200)
        self.assertIn(pending_req1, response_all.context['refund_requests'])
        self.assertIn(approved_req1, response_all.context['refund_requests'])
        self.assertIn(non_expired_unverified, response_all.context['refund_requests'])
        self.assertEqual(len(response_all.context['refund_requests']), 3) # Should include all non-deleted ones

    def test_unauthenticated_user_redirected(self):
        """
        Test that an unauthenticated user is redirected to the login page.
        """
        response = self.client.get(self.management_url)
        # Updated expected redirect URL
        self.assertRedirects(response, f'/admin/login/?next={self.management_url}')

    def test_non_staff_user_redirected_to_login(self):
        """
        Test that a non-staff authenticated user is redirected to the login page
        due to staff_member_required decorator.
        """
        self.client.login(username=self.regular_user.username, password='password123')
        response = self.client.get(self.management_url)
        # Updated expected redirect URL
        self.assertRedirects(response, f'/admin/login/?next={self.management_url}')
