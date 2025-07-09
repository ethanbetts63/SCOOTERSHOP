from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.messages import get_messages
from unittest.mock import patch, MagicMock
from django.utils import timezone
from datetime import timedelta

from payments.models import RefundRequest
from payments.tests.test_helpers.model_factories import UserFactory, RefundRequestFactory, ServiceBookingFactory, SalesBookingFactory, ServiceProfileFactory, SalesProfileFactory

class AdminRefundManagementTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.admin_user = UserFactory(is_staff=True)
        self.client.force_login(self.admin_user)
        self.url = reverse('payments:admin_refund_management')

        # Ensure a clean slate for RefundRequest objects
        RefundRequest.objects.all().delete()

    def test_get_request_basic_display(self):
        RefundRequestFactory.create_batch(5) # Create some refund requests
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'payments/admin_refund_management.html')
        self.assertIn('refund_requests', response.context)
        self.assertEqual(len(response.context['refund_requests']), 5)
        self.assertIn('status_choices', response.context)
        self.assertIn('current_status', response.context)
        self.assertEqual(response.context['current_status'], 'all')

    def test_get_request_with_status_filter(self):
        RefundRequestFactory.create_batch(3, status='pending')
        RefundRequestFactory.create_batch(2, status='approved')

        response = self.client.get(self.url + '?status=pending')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['refund_requests']), 3)
        self.assertEqual(response.context['current_status'], 'pending')

        response = self.client.get(self.url + '?status=approved')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['refund_requests']), 2)
        self.assertEqual(response.context['current_status'], 'approved')

    @patch('payments.views.Refunds.admin_refund_management.send_templated_email')
    @patch('django.utils.timezone.now')
    def test_clean_expired_unverified_refund_requests_deletes_and_sends_email(self, mock_now, mock_send_templated_email):
        # Set mock_now to a specific time
        mock_now.return_value = timezone.now()

        # Create an expired unverified request (older than 24 hours)
        expired_time = mock_now.return_value - timedelta(hours=24, minutes=1)
        expired_request = RefundRequestFactory(status='unverified', token_created_at=expired_time, request_email='expired@example.com')

        # Create a non-expired unverified request
        non_expired_time = mock_now.return_value - timedelta(hours=23)
        non_expired_request = RefundRequestFactory(status='unverified', token_created_at=non_expired_time, request_email='nonexpired@example.com')

        # Create a verified request
        verified_request = RefundRequestFactory(status='pending', request_email='verified@example.com')

        # Access the view to trigger the clean method
        response = self.client.get(self.url)

        # Verify expired request is deleted
        self.assertFalse(RefundRequest.objects.filter(pk=expired_request.pk).exists())
        # Verify non-expired request is not deleted
        self.assertTrue(RefundRequest.objects.filter(pk=non_expired_request.pk).exists())
        # Verify verified request is not deleted
        self.assertTrue(RefundRequest.objects.filter(pk=verified_request.pk).exists())

        # Verify email was sent for the expired request
        mock_send_templated_email.assert_called_once()
        call_args, call_kwargs = mock_send_templated_email.call_args
        self.assertEqual(call_kwargs['recipient_list'], ['expired@example.com'])
        self.assertIn('Your Refund Request for Booking', call_kwargs['subject'])
        self.assertEqual(call_kwargs['template_name'], 'user_refund_request_expired_unverified.html')

    @patch('payments.views.Refunds.admin_refund_management.send_templated_email')
    @patch('django.utils.timezone.now')
    def test_clean_expired_unverified_refund_requests_no_email_sent_if_no_recipient(self, mock_now, mock_send_templated_email):
        mock_now.return_value = timezone.now()
        expired_time = mock_now.return_value - timedelta(hours=24, minutes=1)
        # Create an expired request with no request_email and no user linked to profile
        sales_profile_no_email = SalesProfileFactory(email=None, user=None)
        sales_booking = SalesBookingFactory(sales_profile=sales_profile_no_email)
        expired_request = RefundRequestFactory(status='unverified', token_created_at=expired_time, request_email=None, sales_booking=sales_booking, sales_profile=sales_profile_no_email)

        response = self.client.get(self.url)

        self.assertFalse(RefundRequest.objects.filter(pk=expired_request.pk).exists())
        mock_send_templated_email.assert_not_called()

    def test_admin_required_mixin(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('users:login') + '?next=' + self.url)
