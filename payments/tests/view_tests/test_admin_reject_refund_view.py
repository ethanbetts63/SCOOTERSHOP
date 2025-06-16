# payments/tests/view_tests/test_admin_reject_refund_view.py

from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from unittest.mock import patch

from payments.models import RefundRequest
from payments.tests.test_helpers.model_factories import (
    RefundRequestFactory,
    HireBookingFactory,
    ServiceBookingFactory,
    SalesBookingFactory,
    UserFactory,
)

# The correct path to patch the send_templated_email function used in the view
PATCH_PATH = 'payments.views.Refunds.admin_reject_refund_view.send_templated_email'

class AdminRejectRefundViewTests(TestCase):
    """
    Tests for the AdminRejectRefundView.
    """

    def setUp(self):
        """Set up test data and client for all tests."""
        self.client = Client()
        
        # Create users and explicitly set their passwords for the test client login
        self.admin_user = UserFactory(username='testadmin', is_staff=True, is_superuser=True)
        self.admin_user.set_password('password')
        self.admin_user.save()

        self.regular_user = UserFactory(username='testuser')
        self.regular_user.set_password('password')
        self.regular_user.save()

        # Create refund requests for each booking type to test against
        self.hire_refund_request = RefundRequestFactory(
            hire_booking=HireBookingFactory(),
            status='pending',
            request_email='hire.customer@example.com'
        )
        self.service_refund_request = RefundRequestFactory(
            service_booking=ServiceBookingFactory(),
            status='pending',
            request_email='service.customer@example.com'
        )
        self.sales_refund_request = RefundRequestFactory(
            sales_booking=SalesBookingFactory(),
            status='pending',
            request_email='sales.customer@example.com'
        )
        
        # URL for the view, parameterized in tests
        self.view_url_name = 'payments:reject_refund_request'

    def test_get_reject_form_as_admin(self):
        """Test that an admin can access the GET view."""
        self.client.login(username=self.admin_user.username, password='password')
        
        url = reverse(self.view_url_name, kwargs={'pk': self.hire_refund_request.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'payments/admin_reject_refund_form.html')
        self.assertIn('form', response.context)
        self.assertEqual(response.context['refund_request'], self.hire_refund_request)

    def test_get_reject_form_as_non_admin(self):
        """Test that a non-admin is redirected from the GET view."""
        self.client.login(username=self.regular_user.username, password='password')
        
        url = reverse(self.view_url_name, kwargs={'pk': self.hire_refund_request.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 302)
        # Corrected assertion to check for the correct login URL
        self.assertIn('/accounts/login/', response.url)

    def test_get_reject_form_for_invalid_pk(self):
        """Test that a 404 is returned for a non-existent refund request PK."""
        self.client.login(username=self.admin_user.username, password='password')
        
        url = reverse(self.view_url_name, kwargs={'pk': 9999})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 404)

    @patch(PATCH_PATH)
    def test_post_successful_rejection_with_email(self, mock_send_email):
        """Test successful rejection with the 'send email' checkbox ticked."""
        self.client.login(username=self.admin_user.username, password='password')
        url = reverse(self.view_url_name, kwargs={'pk': self.hire_refund_request.pk})
        rejection_reason = "The refund period has expired."
        
        post_data = {
            'rejection_reason': rejection_reason,
            'send_rejection_email': 'on',
        }
        
        response = self.client.post(url, post_data, follow=True)
        
        # Check final response and redirection
        self.assertEqual(response.status_code, 200)
        self.assertRedirects(response, reverse('payments:admin_refund_management'))

        # Check model state
        self.hire_refund_request.refresh_from_db()
        self.assertEqual(self.hire_refund_request.status, 'rejected')
        self.assertEqual(self.hire_refund_request.rejection_reason, rejection_reason)
        self.assertEqual(self.hire_refund_request.processed_by, self.admin_user)
        self.assertIsNotNone(self.hire_refund_request.processed_at)

        # Check that emails were sent (1 to user, 1 to admin)
        self.assertEqual(mock_send_email.call_count, 2)
        
        # Check user email call
        user_email_call = mock_send_email.call_args_list[0]
        self.assertEqual(user_email_call.kwargs['recipient_list'], ['hire.customer@example.com'])
        self.assertIn('Has Been Rejected', user_email_call.kwargs['subject'])

        # Check messages
        messages = list(response.context['messages'])
        self.assertTrue(any("successfully rejected" in str(m) for m in messages))
        self.assertTrue(any("rejection email sent to the user" in str(m) for m in messages))

    @patch(PATCH_PATH)
    def test_post_successful_rejection_without_email(self, mock_send_email):
        """Test successful rejection without sending an email to the user."""
        self.client.login(username=self.admin_user.username, password='password')
        url = reverse(self.view_url_name, kwargs={'pk': self.service_refund_request.pk})
        rejection_reason = "Internal decision."
        
        post_data = {
            'rejection_reason': rejection_reason,
            # 'send_rejection_email' is omitted
        }
        
        response = self.client.post(url, post_data, follow=True)

        self.service_refund_request.refresh_from_db()
        self.assertEqual(self.service_refund_request.status, 'rejected')

        # Check that only one email was sent (the admin notification)
        self.assertEqual(mock_send_email.call_count, 1)
        
        # Verify it's the admin notification
        admin_email_call = mock_send_email.call_args_list[0]
        self.assertIn('admin', admin_email_call.kwargs['template_name'])
        
        messages = list(response.context['messages'])
        self.assertTrue(any("successfully rejected" in str(m) for m in messages))
        # Ensure the "email sent to user" message is NOT present
        self.assertFalse(any("rejection email sent to the user" in str(m) for m in messages))

    def test_post_invalid_form(self):
        """Test POST with an invalid form (e.g., if validation is added later)."""
        self.client.login(username=self.admin_user.username, password='password')
        url = reverse(self.view_url_name, kwargs={'pk': self.sales_refund_request.pk})

        with patch('payments.forms.admin_reject_refund_form.AdminRejectRefundForm.is_valid', return_value=False):
            response = self.client.post(url, {'rejection_reason': 'This will fail'})
            
            # Should re-render the form page with an error
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, 'payments/admin_reject_refund_form.html')
            self.assertIn("Please correct the errors below", str(response.content))

            # Ensure the model state has not changed
            self.sales_refund_request.refresh_from_db()
            self.assertEqual(self.sales_refund_request.status, 'pending')
