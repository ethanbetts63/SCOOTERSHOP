from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
from django.test import TestCase
from refunds.utils.sales_refund_calc import calculate_sales_refund_amount
from core.tests.test_helpers.model_factories import UserFactory
from refunds.models import RefundSettings

class TestSalesRefundCalc(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.refund_settings = RefundSettings.objects.create(
            deposit_full_refund_days=7,
            deposit_partial_refund_days=3,
            deposit_partial_refund_percentage=50,
            deposit_no_refund_days=1,
        )

    def test_full_refund(self):
        booking = {
            "created_at": timezone.now() - timedelta(days=10),
            "total_paid": Decimal("100.00"),
        }
        result = calculate_sales_refund_amount(booking)
        self.assertEqual(result["entitled_amount"], Decimal("100.00"))
        self.assertIn("Full Refund", result["policy_applied"])

    def test_partial_refund(self):
        booking = {
            "created_at": timezone.now() - timedelta(days=5),
            "total_paid": Decimal("100.00"),
        }
        result = calculate_sales_refund_amount(booking)
        self.assertEqual(result["entitled_amount"], Decimal("50.00"))
        self.assertIn("Partial Refund", result["policy_applied"])

    def test_no_refund(self):
        booking = {
            "created_at": timezone.now() - timedelta(days=2),
            "total_paid": Decimal("100.00"),
        }
        result = calculate_sales_refund_amount(booking)
        self.assertEqual(result["entitled_amount"], Decimal("0.00"))
        self.assertIn("No Refund", result["policy_applied"])

    def test_no_refund_settings(self):
        RefundSettings.objects.all().delete()
        booking = {
            "created_at": timezone.now() - timedelta(days=10),
            "total_paid": Decimal("100.00"),
        }
        result = calculate_sales_refund_amount(booking)
        self.assertEqual(result["entitled_amount"], Decimal("0.00"))
        self.assertEqual(result["details"], "Refund settings not configured.")