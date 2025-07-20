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
        booking_appointment_date = (timezone.now() + timedelta(days=8)).date()
        booking = SalesBookingFactory(appointment_date=booking_appointment_date, amount_paid=Decimal("100.00"))

        result = calculate_sales_refund_amount(booking)

        self.assertEqual(result["entitled_amount"], Decimal("100.00"))
        self.assertIn("Full Refund", result["policy_applied"])

    def test_partial_refund_scenario(self):
        self.refund_settings.deposit_full_refund_days = 7
        self.refund_settings.deposit_partial_refund_days = 3
        self.refund_settings.deposit_no_refund_days = 1
        self.refund_settings.deposit_partial_refund_percentage = Decimal("50.00")
        self.refund_settings.save()
        booking_appointment_date = (timezone.now() + timedelta(days=5)).date()
        booking = SalesBookingFactory(appointment_date=booking_appointment_date, amount_paid=Decimal("100.00"))

        result = calculate_sales_refund_amount(booking)

        self.assertEqual(result["entitled_amount"], Decimal("50.00"))
        self.assertIn("Partial Refund", result["policy_applied"])
        self.assertIn("50.00%", result["policy_applied"])

    def test_no_refund_scenario(self):
        self.refund_settings.deposit_full_refund_days = 7
        self.refund_settings.deposit_partial_refund_days = 3
        self.refund_settings.deposit_no_refund_days = 1
        self.refund_settings.save()
        booking_appointment_date = (timezone.now() + timedelta(days=0)).date()
        booking = SalesBookingFactory(appointment_date=booking_appointment_date, amount_paid=Decimal("100.00"))

        result = calculate_sales_refund_amount(booking)

        self.assertEqual(result["entitled_amount"], Decimal("0.00"))
        self.assertIn("No Refund", result["policy_applied"])

    def test_cancellation_datetime_parameter(self):
        self.refund_settings.deposit_full_refund_days = 7
        self.refund_settings.deposit_partial_refund_days = 3
        self.refund_settings.deposit_no_refund_days = 1
        self.refund_settings.save()
        booking_appointment_date = (timezone.now() + timedelta(days=10)).date()
        booking = SalesBookingFactory(appointment_date=booking_appointment_date, amount_paid=Decimal("100.00"))

        cancellation_datetime = timezone.now() + timedelta(days=5)
        result = calculate_sales_refund_amount(
            booking, cancellation_datetime=cancellation_datetime
        )

        self.assertEqual(result["entitled_amount"], Decimal("50.00"))
        self.assertIn("Partial Refund", result["policy_applied"])

    def test_entitled_amount_never_exceeds_total_paid(self):
        self.refund_settings.deposit_full_refund_days = 7
        self.refund_settings.deposit_partial_refund_days = 3
        self.refund_settings.deposit_no_refund_days = 1
        self.refund_settings.save()
        booking_appointment_date = (timezone.now() + timedelta(days=10)).date()
        booking = SalesBookingFactory(appointment_date=booking_appointment_date, amount_paid=Decimal("50.00"))

        result = calculate_sales_refund_amount(booking)
        self.assertEqual(result["entitled_amount"], Decimal("50.00"))

    def test_entitled_amount_never_less_than_zero(self):
        self.refund_settings.deposit_full_refund_days = 7
        self.refund_settings.deposit_partial_refund_days = 3
        self.refund_settings.deposit_no_refund_days = 1
        self.refund_settings.save()
        booking_appointment_date = (timezone.now() + timedelta(days=1)).date()
        booking = SalesBookingFactory(appointment_date=booking_appointment_date, amount_paid=Decimal("100.00"))

        result = calculate_sales_refund_amount(booking)
        self.assertEqual(result["entitled_amount"], Decimal("0.00"))

    def test_decimal_quantization(self):
        self.refund_settings.deposit_full_refund_days = 7
        self.refund_settings.deposit_partial_refund_days = 3
        self.refund_settings.deposit_no_refund_days = 1
        self.refund_settings.deposit_partial_refund_percentage = Decimal("33.33")
        self.refund_settings.save()
        booking_appointment_date = (timezone.now() + timedelta(days=5)).date()
        booking = SalesBookingFactory(
            appointment_date=booking_appointment_date, amount_paid=Decimal("100.00")
        )

        result = calculate_sales_refund_amount(booking)
        self.assertEqual(result["entitled_amount"], Decimal("33.33"))
        self.assertEqual(
            result["entitled_amount"].as_tuple().exponent, -2
        )  # Check for 2 decimal places
