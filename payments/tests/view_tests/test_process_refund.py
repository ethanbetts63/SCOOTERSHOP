from django.test import TestCase, Client
from django.urls import reverse
from django.contrib import messages
from django.conf import settings
from unittest.mock import patch, MagicMock
from decimal import Decimal
from django.utils import timezone
from datetime import time, timedelta
import stripe

from payments.tests.test_helpers.model_factories import (
    RefundRequestFactory,
    ServiceBookingFactory,
    SalesBookingFactory,
    PaymentFactory,
    UserFactory,
)


settings.STRIPE_SECRET_KEY = "sk_test_dummykey"


class ProcessRefundViewTests(TestCase):

    @classmethod
    def setUpTestData(cls):

        cls.client = Client()
        cls.admin_user = UserFactory(is_staff=True, is_superuser=True)
        cls.regular_user = UserFactory(is_staff=False, is_superuser=False)

    def setUp(self):

        self.client.force_login(self.admin_user)

    @patch("payments.views.Refunds.process_refund.stripe.Refund.create")
    @patch("payments.views.Refunds.process_refund.is_admin", return_value=True)
    def test_successful_service_booking_refund(
        self, mock_is_admin, mock_stripe_refund_create
    ):

        mock_stripe_refund_create.return_value = MagicMock(
            id="re_mockedservice456", status="succeeded"
        )

        service_booking = ServiceBookingFactory(
            payment=PaymentFactory(
                stripe_payment_intent_id="pi_service456",
                amount=Decimal("200.00"),
                status="succeeded",
                refund_policy_snapshot={"key": "value"},
            ),
            dropoff_date=timezone.now().date() + timedelta(days=10),
            dropoff_time=time(9, 0),
            service_booking_reference="SERVICEBOOKINGREF",
        )

        refund_request = RefundRequestFactory(
            service_booking=service_booking,
            sales_booking=None,
            payment=service_booking.payment,
            status="reviewed_pending_approval",
            amount_to_refund=Decimal("100.00"),
            stripe_refund_id=None,
            processed_by=None,
            processed_at=None,
        )

        url = reverse("payments:process_refund", kwargs={"pk": refund_request.pk})
        response = self.client.post(url)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("payments:admin_refund_management"))

        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 1)
        self.assertIn(
            f"Refund request for booking '{service_booking.service_booking_reference}' has been approved and initiated with Stripe (ID: {mock_stripe_refund_create.return_value.id}). Awaiting final confirmation from Stripe.",
            str(messages_list[0]),
        )
        self.assertEqual(messages_list[0].tags, "success")

        mock_stripe_refund_create.assert_called_once_with(
            payment_intent="pi_service456",
            amount=int(Decimal("100.00") * 100),
            reason="requested_by_customer",
            metadata={
                "refund_request_id": str(refund_request.pk),
                "admin_user_id": str(self.admin_user.pk),
                "booking_reference": "SERVICEBOOKINGREF",
                "booking_type": "service",
            },
        )

        refund_request.refresh_from_db()
        self.assertEqual(refund_request.status, "approved")
        self.assertEqual(refund_request.stripe_refund_id, "re_mockedservice456")
        self.assertEqual(refund_request.processed_by, self.admin_user)
        self.assertIsNotNone(refund_request.processed_at)

    @patch("payments.views.Refunds.process_refund.stripe.Refund.create")
    @patch("payments.views.Refunds.process_refund.is_admin", return_value=True)
    def test_successful_sales_booking_refund(
        self, mock_is_admin, mock_stripe_refund_create
    ):

        mock_stripe_refund_create.return_value = MagicMock(
            id="re_mockedsales789", status="succeeded"
        )

        sales_booking = SalesBookingFactory(
            payment=PaymentFactory(
                stripe_payment_intent_id="pi_sales789",
                amount=Decimal("150.00"),
                status="succeeded",
                refund_policy_snapshot={"key": "value"},
            ),
            appointment_date=timezone.now().date() + timedelta(days=7),
            sales_booking_reference="SALESBOOKINGREF",
        )

        refund_request = RefundRequestFactory(
            service_booking=None,
            sales_booking=sales_booking,
            payment=sales_booking.payment,
            status="pending",
            amount_to_refund=Decimal("75.00"),
            stripe_refund_id=None,
            processed_by=None,
            processed_at=None,
        )

        url = reverse("payments:process_refund", kwargs={"pk": refund_request.pk})
        response = self.client.post(url)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("payments:admin_refund_management"))

        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 1)
        self.assertIn(
            f"Refund request for booking '{sales_booking.sales_booking_reference}' has been approved and initiated with Stripe (ID: {mock_stripe_refund_create.return_value.id}). Awaiting final confirmation from Stripe.",
            str(messages_list[0]),
        )
        self.assertEqual(messages_list[0].tags, "success")

        mock_stripe_refund_create.assert_called_once_with(
            payment_intent="pi_sales789",
            amount=int(Decimal("75.00") * 100),
            reason="requested_by_customer",
            metadata={
                "refund_request_id": str(refund_request.pk),
                "admin_user_id": str(self.admin_user.pk),
                "booking_reference": "SALESBOOKINGREF",
                "booking_type": "sales",
            },
        )

        refund_request.refresh_from_db()
        self.assertEqual(refund_request.status, "approved")
        self.assertEqual(refund_request.stripe_refund_id, "re_mockedsales789")
        self.assertEqual(refund_request.processed_by, self.admin_user)
        self.assertIsNotNone(refund_request.processed_at)

    @patch("payments.views.Refunds.process_refund.is_admin", return_value=True)
    def test_refund_invalid_status_rejection(self, mock_is_admin):

        refund_request = RefundRequestFactory(
            status="failed",
            amount_to_refund=Decimal("50.00"),
            payment=PaymentFactory(stripe_payment_intent_id="pi_test"),
        )
        url = reverse("payments:process_refund", kwargs={"pk": refund_request.pk})
        response = self.client.post(url)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("payments:admin_refund_management"))

        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 1)
        self.assertIn(
            "Refund request is not in an approvable state. Current status: Refund Failed.",
            str(messages_list[0]),
        )
        self.assertEqual(messages_list[0].tags, "error")

        refund_request.refresh_from_db()
        self.assertEqual(refund_request.status, "failed")

    @patch("payments.views.Refunds.process_refund.is_admin", return_value=True)
    def test_refund_no_associated_payment_rejection(self, mock_is_admin):

        refund_request = RefundRequestFactory(
            status="pending", amount_to_refund=Decimal("50.00"), payment=None
        )
        url = reverse("payments:process_refund", kwargs={"pk": refund_request.pk})
        response = self.client.post(url)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("payments:admin_refund_management"))

        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 1)
        self.assertIn(
            "Cannot process refund: No associated payment found for this request.",
            str(messages_list[0]),
        )
        self.assertEqual(messages_list[0].tags, "error")

        refund_request.refresh_from_db()
        self.assertEqual(refund_request.status, "pending")

    @patch("payments.views.Refunds.process_refund.is_admin", return_value=True)
    def test_refund_invalid_amount_rejection(self, mock_is_admin):

        refund_request = RefundRequestFactory(
            status="pending",
            amount_to_refund=Decimal("0.00"),
            payment=PaymentFactory(stripe_payment_intent_id="pi_test"),
        )
        url = reverse("payments:process_refund", kwargs={"pk": refund_request.pk})
        response = self.client.post(url)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("payments:admin_refund_management"))

        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 1)
        self.assertIn(
            "Cannot process refund: No valid amount specified to refund.",
            str(messages_list[0]),
        )
        self.assertEqual(messages_list[0].tags, "error")

        refund_request.refresh_from_db()

        self.assertEqual(refund_request.status, "pending")

    @patch("payments.views.Refunds.process_refund.is_admin", return_value=True)
    def test_refund_no_stripe_payment_intent_id_rejection(self, mock_is_admin):

        refund_request = RefundRequestFactory(
            status="pending",
            amount_to_refund=Decimal("50.00"),
            payment=PaymentFactory(stripe_payment_intent_id=None),
        )
        url = reverse("payments:process_refund", kwargs={"pk": refund_request.pk})
        response = self.client.post(url)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("payments:admin_refund_management"))

        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 1)
        self.assertIn(
            "Cannot process refund: Associated payment has no Stripe Payment Intent ID.",
            str(messages_list[0]),
        )
        self.assertEqual(messages_list[0].tags, "error")

        refund_request.refresh_from_db()

        self.assertEqual(refund_request.status, "pending")

    @patch("payments.views.Refunds.process_refund.stripe.Refund.create")
    @patch("payments.views.Refunds.process_refund.is_admin", return_value=True)
    def test_generic_exception_during_refund_creation(
        self, mock_is_admin, mock_stripe_refund_create
    ):

        mock_stripe_refund_create.side_effect = ValueError(
            "Something went wrong internally"
        )

        service_booking = ServiceBookingFactory(
            payment=PaymentFactory(
                stripe_payment_intent_id="pi_generic_error",
                amount=Decimal("100.00"),
                status="succeeded",
                refund_policy_snapshot={"key": "value"},
            ),
            dropoff_date=timezone.now().date() + timedelta(days=10),
            dropoff_time=time(9, 0),
            service_booking_reference="SERVICEERR",
        )

        refund_request = RefundRequestFactory(
            service_booking=service_booking,
            sales_booking=None,
            payment=service_booking.payment,
            status="reviewed_pending_approval",
            amount_to_refund=Decimal("50.00"),
            stripe_refund_id=None,
            processed_by=None,
            processed_at=None,
        )

        url = reverse("payments:process_refund", kwargs={"pk": refund_request.pk})
        response = self.client.post(url)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("payments:admin_refund_management"))

        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 1)
        self.assertIn(
            "An unexpected error occurred: Something went wrong internally",
            str(messages_list[0]),
        )
        self.assertEqual(messages_list[0].tags, "error")

        mock_stripe_refund_create.assert_called_once()

        refund_request.refresh_from_db()
        self.assertEqual(refund_request.status, "failed")
        self.assertIn(
            "Unexpected error during initiation: Something went wrong internally",
            refund_request.staff_notes,
        )
        self.assertIsNone(refund_request.stripe_refund_id)
        self.assertIsNone(refund_request.processed_by)
        self.assertIsNone(refund_request.processed_at)

    @patch("payments.views.Refunds.process_refund.is_admin", return_value=False)
    def test_unauthorized_access(self, mock_is_admin):

        self.client.force_login(self.regular_user)

        refund_request = RefundRequestFactory(
            status="approved",
            amount_to_refund=Decimal("50.00"),
            payment=PaymentFactory(stripe_payment_intent_id="pi_unauth"),
        )
        url = reverse("payments:process_refund", kwargs={"pk": refund_request.pk})
        response = self.client.post(url)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("users:login") + "?next=" + url)

        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 0)

        refund_request.refresh_from_db()
        self.assertEqual(refund_request.status, "approved")
