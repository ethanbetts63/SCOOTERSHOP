import datetime
from django.test import TestCase, Client
from django.urls import reverse
from unittest.mock import patch, ANY
from refunds.forms.admin_reject_refund_form import AdminRejectRefundForm
from payments.tests.test_helpers.model_factories import (
    UserFactory,
    RefundRequestFactory,
    ServiceBookingFactory,
    SalesBookingFactory,
    SalesProfileFactory,
)
from django.utils import timezone
from django.conf import settings


class AdminRejectRefundViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = StaffUserFactory()
        self.client.force_login(self.admin_user)
        self.service_booking = ServiceBookingFactory()
        self.sales_booking = SalesBookingFactory()
        self.refund_request_service = RefundRequestFactory(
            service_booking=self.service_booking, status="pending"
        )
        self.refund_request_sales = RefundRequestFactory(
            sales_booking=self.sales_booking, status="pending"
        )

    def test_get_reject_refund_request_service_booking(self):
        url = reverse(
            "refunds:reject_refund_request",
            kwargs={"pk": self.refund_request_service.pk},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "refunds/admin_reject_refund_form.html")
        self.assertIsInstance(response.context["form"], AdminRejectRefundForm)
        self.assertEqual(
            response.context["refund_request"], self.refund_request_service
        )
        self.assertIn(
            f"Reject Refund Request for Booking {self.service_booking.service_booking_reference}",
            response.context["title"],
        )

    def test_get_reject_refund_request_sales_booking(self):
        url = reverse(
            "refunds:reject_refund_request", kwargs={"pk": self.refund_request_sales.pk}
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "refunds/admin_reject_refund_form.html")
        self.assertIsInstance(response.context["form"], AdminRejectRefundForm)
        self.assertEqual(response.context["refund_request"], self.refund_request_sales)
        self.assertIn(
            f"Reject Refund Request for Booking {self.sales_booking.sales_booking_reference}",
            response.context["title"],
        )

    # This test is failing because the URL pattern expects a numeric PK, but a UUID string is passed.
    # The URL pattern is defined as 'refunds/settings/refunds/reject/(?P<pk>[0-9]+)/\Z'.
    # To fix this, the test should pass a non-existent integer PK instead of a UUID string.
    def test_get_reject_refund_request_invalid_pk(self):
        url = reverse("refunds:reject_refund_request", kwargs={"pk": 999999})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    # This test is failing due to a TypeError: fromisoformat: argument must be str.
    # This indicates an issue with factory_boy's interaction with mocked timezone.now() when creating objects.
    # The problem is not in the test logic itself, but in the interaction with the mocking and factory.
    @patch("payments.views.Refunds.admin_reject_refund_view.send_templated_email")
    @patch("django.contrib.messages.success")
    @patch("django.contrib.messages.info")
    def test_post_reject_refund_request_send_email_to_user(
        self, mock_messages_info, mock_messages_success, mock_send_templated_email
    ):
        now = timezone.now()
        url = reverse(
            "refunds:reject_refund_request",
            kwargs={"pk": self.refund_request_service.pk},
        )
        form_data = {
            "rejection_reason": "Test rejection reason",
            "send_rejection_email": True,
        }
        with patch("django.utils.timezone.now") as mock_now:
            mock_now.return_value = now
            response = self.client.post(url, data=form_data)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("refunds:admin_refund_management"))

        self.refund_request_service.refresh_from_db()
        self.assertEqual(self.refund_request_service.status, "rejected")
        self.assertEqual(
            self.refund_request_service.rejection_reason, "Test rejection reason"
        )
        self.assertEqual(self.refund_request_service.processed_by, self.admin_user)
        self.assertEqual(self.refund_request_service.processed_at, now)

        mock_messages_success.assert_called_once_with(
            ANY,
            f"Refund Request for booking '{self.service_booking.service_booking_reference}' has been successfully rejected.",
        )
        self.assertEqual(mock_send_templated_email.call_count, 2)

        user_email_call = mock_send_templated_email.call_args_list[0]
        self.assertEqual(
            user_email_call.kwargs["recipient_list"],
            [self.refund_request_service.request_email],
        )
        self.assertIn(
            "Your Refund Request for Booking", user_email_call.kwargs["subject"]
        )
        self.assertEqual(
            user_email_call.kwargs["template_name"], "user_refund_request_rejected.html"
        )
        mock_messages_info.assert_any_call(
            ANY, "Automated rejection email sent to the user."
        )

        admin_email_call = mock_send_templated_email.call_args_list[1]
        self.assertEqual(
            admin_email_call.kwargs["recipient_list"], [settings.DEFAULT_FROM_EMAIL]
        )
        self.assertIn("Refund Request", admin_email_call.kwargs["subject"])
        self.assertEqual(
            admin_email_call.kwargs["template_name"],
            "admin_refund_request_rejected.html",
        )
        mock_messages_info.assert_any_call(
            ANY, "Admin notification email sent regarding the rejection."
        )

    # This test is failing due to the same TypeError as test_post_reject_refund_request_send_email_to_user.
    @patch("payments.views.Refunds.admin_reject_refund_view.send_templated_email")
    @patch("django.contrib.messages.success")
    @patch("django.contrib.messages.info")
    def test_post_reject_refund_request_do_not_send_email_to_user(
        self, mock_messages_info, mock_messages_success, mock_send_templated_email
    ):
        now = timezone.now()
        url = reverse(
            "refunds:reject_refund_request",
            kwargs={"pk": self.refund_request_service.pk},
        )
        form_data = {
            "rejection_reason": "Test rejection reason",
            "send_rejection_email": False,
        }
        with patch("django.utils.timezone.now") as mock_now:
            mock_now.return_value = now
            response = self.client.post(url, data=form_data)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("refunds:admin_refund_management"))

        self.refund_request_service.refresh_from_db()
        self.assertEqual(self.refund_request_service.status, "rejected")
        self.assertEqual(
            self.refund_request_service.rejection_reason, "Test rejection reason"
        )

        mock_messages_success.assert_called_once()
        self.assertEqual(mock_send_templated_email.call_count, 1)

        admin_email_call = mock_send_templated_email.call_args_list[0]
        self.assertEqual(
            admin_email_call.kwargs["recipient_list"], [settings.DEFAULT_FROM_EMAIL]
        )
        self.assertIn("Refund Request", admin_email_call.kwargs["subject"])

    @patch("django.contrib.messages.error")
    def test_post_reject_refund_request_optional_rejection_reason(
        self, mock_messages_error
    ):
        url = reverse(
            "refunds:reject_refund_request",
            kwargs={"pk": self.refund_request_service.pk},
        )
        form_data = {
            "rejection_reason": "",
            "send_rejection_email": True,
        }
        response = self.client.post(url, data=form_data)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("refunds:admin_refund_management"))
        self.refund_request_service.refresh_from_db()
        self.assertEqual(self.refund_request_service.status, "rejected")
        self.assertEqual(self.refund_request_service.rejection_reason, "")

    # This test is failing due to the same TypeError as test_post_reject_refund_request_send_email_to_user.
    @patch("payments.views.Refunds.admin_reject_refund_view.send_templated_email")
    @patch("django.contrib.messages.warning")
    @patch("django.contrib.messages.success")
    def test_post_reject_refund_request_no_user_recipient_email(
        self, mock_messages_success, mock_messages_warning, mock_send_templated_email
    ):
        now = datetime.datetime(2025, 7, 9, 10, 0, 0, tzinfo=datetime.timezone.utc)
        sales_profile_no_email = SalesProfileFactory(
            email="valid@example.com", user=None
        )
        sales_booking = SalesBookingFactory(sales_profile=sales_profile_no_email)
        refund_request_no_email = RefundRequestFactory(
            sales_booking=sales_booking, request_email=None, status="pending"
        )

        url = reverse(
            "refunds:reject_refund_request", kwargs={"pk": refund_request_no_email.pk}
        )
        form_data = {
            "rejection_reason": "Test rejection reason",
            "send_rejection_email": True,
        }
        with patch("django.utils.timezone.now") as mock_now:
            mock_now.return_value = now
            response = self.client.post(url, data=form_data)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("refunds:admin_refund_management"))

        refund_request_no_email.refresh_from_db()
        self.assertEqual(refund_request_no_email.status, "rejected")

        mock_messages_warning.assert_called_once_with(
            response.wsgi_request,
            "Could not send automated rejection email to user: No recipient email found.",
        )
        self.assertEqual(mock_send_templated_email.call_count, 1)

        admin_email_call = mock_send_templated_email.call_args_list[0]
        self.assertEqual(
            admin_email_call.kwargs["recipient_list"], [settings.DEFAULT_FROM_EMAIL]
        )

    def test_admin_required_mixin(self):
        self.client.logout()
        url = reverse(
            "refunds:reject_refund_request",
            kwargs={"pk": self.refund_request_service.pk},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("users:login") + "?next=" + url)
