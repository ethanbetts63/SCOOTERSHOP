
from django.test import TestCase
from decimal import Decimal
from refunds.utils.create_refund_request import create_refund_request
from refunds.tests.util_tests.model_factories import (
    ServiceBookingFactory,
    SalesBookingFactory,
    UserFactory,
    ServiceProfileFactory,
    SalesProfileFactory,
)
from refunds.models import RefundRequest

class TestCreateRefundRequest(TestCase):
    def test_create_refund_for_service_booking(self):
        service_booking = ServiceBookingFactory()
        refund_request = create_refund_request(
            amount_to_refund=Decimal("50.00"),
            reason="Test refund",
            service_booking=service_booking,
            service_profile=service_booking.service_profile,
        )
        self.assertIsInstance(refund_request, RefundRequest)
        self.assertEqual(refund_request.amount_to_refund, Decimal("50.00"))
        self.assertEqual(refund_request.service_booking, service_booking)

    def test_create_refund_for_sales_booking(self):
        sales_booking = SalesBookingFactory()
        refund_request = create_refund_request(
            amount_to_refund=Decimal("100.00"),
            reason="Test refund",
            sales_booking=sales_booking,
            sales_profile=sales_booking.sales_profile,
        )
        self.assertIsInstance(refund_request, RefundRequest)
        self.assertEqual(refund_request.amount_to_refund, Decimal("100.00"))
        self.assertEqual(refund_request.sales_booking, sales_booking)

    def test_admin_initiated_refund(self):
        user = UserFactory()
        refund_request = create_refund_request(
            amount_to_refund=Decimal("25.00"),
            reason="Admin initiated refund",
            is_admin_initiated=True,
            requesting_user=user,
        )
        self.assertTrue(refund_request.is_admin_initiated)
        self.assertEqual(refund_request.processed_by, user)
