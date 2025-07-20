from django.test import TestCase
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
from refunds.utils.sales_refund_calc import calculate_sales_refund_amount
from refunds.tests.test_helpers.model_factories import RefundSettingsFactory
from inventory.tests.test_helpers.model_factories import SalesBookingFactory

class SalesRefundCalcTest(TestCase):
    def setUp(self):
        self.refund_settings = RefundSettingsFactory()

    def test_no_refund_settings_configured(self):
        booking = SalesBookingFactory(created_at=timezone.now(), amount_paid=Decimal("100.00"))
        result = calculate_sales_refund_amount(booking)

        self.assertEqual(result["entitled_amount"], Decimal("0.00"))
        self.assertEqual(result["details"], "Refund settings not configured.")
        self.assertEqual(result["policy_applied"], "N/A")

    def test_full_refund_scenario(self):
        self.refund_settings.deposit_full_refund_days = 7
        self.refund_settings.deposit_partial_refund_days = 3
        self.refund_settings.deposit_no_refund_days = 1
        self.refund_settings.save()
        booking_created_at = timezone.now() - timedelta(days=8)  # 8 days ago
        booking = SalesBookingFactory(created_at=booking_created_at, amount_paid=Decimal("100.00"))

        result = calculate_sales_refund_amount(booking)

        self.assertEqual(result["entitled_amount"], Decimal("100.00"))
        self.assertIn("Full Refund", result["policy_applied"])

    def test_partial_refund_scenario(self):
        self.refund_settings.deposit_full_refund_days = 7
        self.refund_settings.deposit_partial_refund_days = 3
        self.refund_settings.deposit_no_refund_days = 1
        self.refund_settings.deposit_partial_refund_percentage = Decimal("50.00")
        self.refund_settings.save()
        booking_created_at = timezone.now() - timedelta(days=5)  # 5 days ago
        booking = SalesBookingFactory(created_at=booking_created_at, amount_paid=Decimal("100.00"))

        result = calculate_sales_refund_amount(booking)

        self.assertEqual(result["entitled_amount"], Decimal("50.00"))
        self.assertIn("Partial Refund", result["policy_applied"])
        self.assertIn("50.00%", result["policy_applied"])

    def test_no_refund_scenario(self):
        self.refund_settings.deposit_full_refund_days = 7
        self.refund_settings.deposit_partial_refund_days = 3
        self.refund_settings.deposit_no_refund_days = 1
        self.refund_settings.save()
        booking_created_at = timezone.now() - timedelta(days=0)  # Less than 1 day ago
        booking = SalesBookingFactory(created_at=booking_created_at, amount_paid=Decimal("100.00"))

        result = calculate_sales_refund_amount(booking)

        self.assertEqual(result["entitled_amount"], Decimal("0.00"))
        self.assertIn("No Refund", result["policy_applied"])

    def test_cancellation_datetime_parameter(self):
        self.refund_settings.deposit_full_refund_days = 7
        self.refund_settings.deposit_partial_refund_days = 3
        self.refund_settings.deposit_no_refund_days = 1
        self.refund_settings.save()
        booking_created_at = timezone.now() - timedelta(days=10)  # 10 days ago
        booking = SalesBookingFactory(created_at=booking_created_at, amount_paid=Decimal("100.00"))

        # Calculate refund as if cancelled 5 days after booking
        cancellation_datetime = booking_created_at + timedelta(days=5)
        result = calculate_sales_refund_amount(
            booking, cancellation_datetime=cancellation_datetime
        )

        # This should fall into partial refund based on the 5-day difference
        self.assertEqual(result["entitled_amount"], Decimal("50.00"))
        self.assertIn("Partial Refund", result["policy_applied"])

    def test_entitled_amount_never_exceeds_total_paid(self):
        self.refund_settings.deposit_full_refund_days = 7
        self.refund_settings.deposit_partial_refund_days = 3
        self.refund_settings.deposit_no_refund_days = 1
        self.refund_settings.save()
        booking_created_at = timezone.now() - timedelta(days=10)  # 10 days ago
        booking = SalesBookingFactory(created_at=booking_created_at, amount_paid=Decimal("50.00"))

        result = calculate_sales_refund_amount(booking)
        self.assertEqual(result["entitled_amount"], Decimal("50.00"))

    def test_entitled_amount_never_less_than_zero(self):
        self.refund_settings.deposit_full_refund_days = 7
        self.refund_settings.deposit_partial_refund_days = 3
        self.refund_settings.deposit_no_refund_days = 1
        self.refund_settings.save()
        booking_created_at = timezone.now() - timedelta(days=1)  # 1 day ago
        booking = SalesBookingFactory(created_at=booking_created_at, amount_paid=Decimal("100.00"))

        result = calculate_sales_refund_amount(booking)
        self.assertEqual(result["entitled_amount"], Decimal("0.00"))

    def test_decimal_quantization(self):
        self.refund_settings.deposit_full_refund_days = 7
        self.refund_settings.deposit_partial_refund_days = 3
        self.refund_settings.deposit_no_refund_days = 1
        self.refund_settings.deposit_partial_refund_percentage = Decimal("33.33")
        self.refund_settings.save()
        booking_created_at = timezone.now() - timedelta(days=5)
        booking = SalesBookingFactory(
            created_at=booking_created_at, amount_paid=Decimal("100.00")
        )

        result = calculate_sales_refund_amount(booking)
        self.assertEqual(result["entitled_amount"], Decimal("33.33"))
        self.assertEqual(
            result["entitled_amount"].as_tuple().exponent, -2
        )  # Check for 2 decimal places
