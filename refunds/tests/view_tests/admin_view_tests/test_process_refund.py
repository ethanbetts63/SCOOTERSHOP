from django.test import TestCase, Client
from django.urls import reverse
from django.contrib import messages
from django.conf import settings
from unittest.mock import patch, MagicMock
from decimal import Decimal

from refunds.tests.test_helpers.model_factories import RefundRequestFactory
from service.tests.test_helpers.model_factories import ServiceBookingFactory
from inventory.tests.test_helpers.model_factories import SalesBookingFactory
from payments.tests.test_helpers.model_factories import PaymentFactory
from users.tests.test_helpers.model_factories import UserFactory, SuperUserFactory

settings.STRIPE_SECRET_KEY = "sk_test_dummykey"


class ProcessRefundViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        cls.admin_user = SuperUserFactory()
        cls.regular_user = UserFactory()

    def setUp(self):
        self.client.force_login(self.admin_user)

    @patch("refunds.views.admin_views.process_refund.stripe.Refund.create")
    def test_successful_service_booking_refund(self, mock_stripe_refund_create):
        mock_stripe_refund_create.return_value = MagicMock(
            id="re_mockedservice456", status="succeeded"
        )

        service_booking = ServiceBookingFactory(
            payment=PaymentFactory(
                stripe_payment_intent_id="pi_service456",
                amount=Decimal("200.00"),
                status="succeeded",
            ),
            service_booking_reference="SERVICEBOOKINGREF",
        )

        refund_request = RefundRequestFactory(
            service_booking=service_booking,
            payment=service_booking.payment,
            status="reviewed_pending_approval",
            amount_to_refund=Decimal("100.00"),
        )

        url = reverse("refunds:process_refund", kwargs={"pk": refund_request.pk})
        response = self.client.post(url)

        self.assertEqual(response.status_code, 302)
        refund_request.refresh_from_db()
        self.assertEqual(refund_request.status, "approved")
        self.assertEqual(refund_request.stripe_refund_id, "re_mockedservice456")

    @patch("refunds.views.admin_views.process_refund.stripe.Refund.create")
    def test_successful_sales_booking_refund(self, mock_stripe_refund_create):
        mock_stripe_refund_create.return_value = MagicMock(
            id="re_mockedsales789", status="succeeded"
        )

        sales_booking = SalesBookingFactory(
            payment=PaymentFactory(
                stripe_payment_intent_id="pi_sales789",
                amount=Decimal("150.00"),
                status="succeeded",
            ),
            sales_booking_reference="SALESBOOKINGREF",
        )

        refund_request = RefundRequestFactory(
            sales_booking=sales_booking,
            payment=sales_booking.payment,
            status="pending",
            amount_to_refund=Decimal("75.00"),
        )

        url = reverse("refunds:process_refund", kwargs={"pk": refund_request.pk})
        response = self.client.post(url)

        self.assertEqual(response.status_code, 302)
        refund_request.refresh_from_db()
        self.assertEqual(refund_request.status, "approved")
        self.assertEqual(refund_request.stripe_refund_id, "re_mockedsales789")

    def test_refund_invalid_status_rejection(self):
        # This test is correct, it specifically checks for a non-approvable status
        refund_request = RefundRequestFactory(status="failed")
        url = reverse("refunds:process_refund", kwargs={"pk": refund_request.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertIn("not in an approvable state", str(messages_list[0]))

    def test_refund_no_associated_payment_rejection(self):
        # FIX: Set an approvable status to get past the first check
        refund_request = RefundRequestFactory(status="pending", payment=None)
        url = reverse("refunds:process_refund", kwargs={"pk": refund_request.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertIn("No associated payment found", str(messages_list[0]))

    def test_refund_invalid_amount_rejection(self):
        # FIX: Set an approvable status to get past the first check
        refund_request = RefundRequestFactory(
            status="pending", amount_to_refund=Decimal("0.00")
        )
        url = reverse("refunds:process_refund", kwargs={"pk": refund_request.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertIn("No valid amount specified", str(messages_list[0]))

    def test_refund_no_stripe_payment_intent_id_rejection(self):
        # FIX: Set an approvable status to get past the first check
        payment = PaymentFactory(stripe_payment_intent_id=None)
        refund_request = RefundRequestFactory(status="pending", payment=payment)
        url = reverse("refunds:process_refund", kwargs={"pk": refund_request.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertIn("no Stripe Payment Intent ID", str(messages_list[0]))

    @patch("refunds.views.admin_views.process_refund.stripe.Refund.create")
    def test_generic_exception_during_refund_creation(self, mock_stripe_refund_create):
        mock_stripe_refund_create.side_effect = ValueError(
            "Something went wrong internally"
        )
        refund_request = RefundRequestFactory(status="reviewed_pending_approval")
        url = reverse("refunds:process_refund", kwargs={"pk": refund_request.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertIn("An unexpected error occurred", str(messages_list[0]))
        refund_request.refresh_from_db()
        self.assertEqual(refund_request.status, "failed")
