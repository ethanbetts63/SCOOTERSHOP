from django.test import TestCase
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
from refunds.utils.sales_refund_calc import calculate_sales_refund_amount
from refunds.models import RefundSettings
from inventory.models import SalesBooking

class SalesRefundCalcTest(TestCase):

    def setUp(self):
        self.refund_settings = RefundSettings.objects.create(
            deposit_full_refund_days=14,
            deposit_partial_refund_days=7,
            deposit_partial_refund_percentage=Decimal("50.00"),
            deposit_no_refund_days=2,
        )

    def create_booking(self, days_ago, amount_paid):
        return SalesBooking.objects.create(
            created_at=timezone.now() - timedelta(days=days_ago),
            amount_paid=Decimal(amount_paid)
        )

    def test_full_refund(self):
        booking = self.create_booking(15, "100.00")
        result = calculate_sales_refund_amount(booking)
        self.assertEqual(result["entitled_amount"], Decimal("100.00"))

    def test_partial_refund(self):
        booking = self.create_booking(8, "100.00")
        result = calculate_sales_refund_amount(booking)
        self.assertEqual(result["entitled_amount"], Decimal("50.00"))

    def test_no_refund(self):
        booking = self.create_booking(3, "100.00")
        result = calculate_sales_refund_amount(booking)
        self.assertEqual(result["entitled_amount"], Decimal("0.00"))