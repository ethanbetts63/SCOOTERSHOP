import datetime
from django.test import TestCase, Client
from django.urls import reverse
from unittest.mock import patch
from django.utils import timezone
from datetime import timedelta

from django.apps import apps
from refunds.tests.test_helpers.model_factories import RefundRequestFactory
from inventory.tests.test_helpers.model_factories import SalesBookingFactory, SalesProfileFactory
from users.tests.test_helpers.model_factories import UserFactory, StaffUserFactory

RefundRequest = apps.get_model('refunds', 'RefundRequest')


class AdminRefundManagementTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = StaffUserFactory()
        self.client.force_login(self.admin_user)
        self.url = reverse("refunds:admin_refund_management")

        RefundRequestFactory.reset_sequence()

    def test_get_request_basic_display(self):
        RefundRequestFactory.create_batch(5)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "refunds/admin_refund_management.html")
        self.assertIn("refund_requests", response.context)
        self.assertEqual(len(response.context["refund_requests"]), 5)
        self.assertIn("status_choices", response.context)
        self.assertIn("current_status", response.context)
        self.assertEqual(response.context["current_status"], "all")

    def test_get_request_with_status_filter(self):
        RefundRequestFactory.create_batch(3, status="pending")
        RefundRequestFactory.create_batch(2, status="approved")

        response = self.client.get(self.url + "?status=pending")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["refund_requests"]), 3)
        self.assertEqual(response.context["current_status"], "pending")

        response = self.client.get(self.url + "?status=approved")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["refund_requests"]), 2)
        self.assertEqual(response.context["current_status"], "approved")

    # This test is failing due to a ValueError: Failed to insert expression "<MagicMock name='now().resolve_expression()' id='...'>" on payments.Payment.created_at.
    # This indicates an issue with factory_boy's interaction with mocked timezone.now() when creating objects.
    # The problem is not in the test logic itself, but in the interaction with the mocking and factory.
    @patch("refunds.views.admin_views.admin_refund_management.send_templated_email")
    def test_clean_expired_unverified_refund_requests_deletes_and_sends_email(
        self, mock_send_templated_email
    ):
        now = timezone.now()
        expired_time = now - timedelta(hours=24, minutes=1)
        expired_request = RefundRequestFactory(
            status="unverified",
            token_created_at=expired_time,
            request_email="expired@example.com",
        )

        non_expired_time = now - timedelta(hours=23)
        non_expired_request = RefundRequestFactory(
            status="unverified",
            token_created_at=non_expired_time,
            request_email="nonexpired@example.com",
        )

        verified_request = RefundRequestFactory(
            status="pending", request_email="verified@example.com"
        )
        with patch("django.utils.timezone.now") as mock_now:
            mock_now.return_value = now
            response = self.client.get(self.url)

        self.assertFalse(RefundRequest.objects.filter(pk=expired_request.pk).exists())
        self.assertTrue(
            RefundRequest.objects.filter(pk=non_expired_request.pk).exists()
        )
        self.assertTrue(RefundRequest.objects.filter(pk=verified_request.pk).exists())

        mock_send_templated_email.assert_called_once()
        call_args, call_kwargs = mock_send_templated_email.call_args
        self.assertEqual(call_kwargs["recipient_list"], ["expired@example.com"])
        self.assertIn("Your Refund Request for Booking", call_kwargs["subject"])
        self.assertEqual(
            call_kwargs["template_name"], "user_refund_request_expired_unverified.html"
        )

    # This test is failing due to the same ValueError as test_clean_expired_unverified_refund_requests_deletes_and_sends_email.
    @patch("refunds.views.admin_views.admin_refund_management.send_templated_email")
    def test_clean_expired_unverified_refund_requests_no_email_sent_if_no_recipient(
        self, mock_send_templated_email
    ):
        now = datetime.datetime(2025, 7, 9, 10, 0, 0, tzinfo=datetime.timezone.utc)
        expired_time = now - timedelta(hours=24, minutes=1)
        sales_profile_no_email = SalesProfileFactory(
            email="valid@example.com", user=None
        )
        sales_booking = SalesBookingFactory(sales_profile=sales_profile_no_email)
        expired_request = RefundRequestFactory(
            status="unverified",
            token_created_at=expired_time,
            request_email=None,
            sales_booking=sales_booking,
            sales_profile=sales_profile_no_email,
        )

        with patch("django.utils.timezone.now") as mock_now:
            mock_now.return_value = now
            response = self.client.get(self.url)

        self.assertFalse(RefundRequest.objects.filter(pk=expired_request.pk).exists())
        mock_send_templated_email.assert_not_called()

    def test_admin_required_mixin(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("users:login") + "?next=" + self.url)
