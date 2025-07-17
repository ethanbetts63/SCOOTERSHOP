from django.test import TestCase
from decimal import Decimal
from datetime import datetime, timedelta, time
from django.utils import timezone
from refunds.utils.service_refund_calc import calculate_service_refund_amount
from refunds.models import RefundSettings
from service.models import ServiceBooking
from service.tests.test_helpers.model_factories import ServiceBookingFactory
from refunds.tests.test_helpers.model_factories import RefundSettingsFactory

class ServiceRefundCalcTest(TestCase):

    def setUp(self):
        RefundSettings.objects.all().delete()
        ServiceBooking.objects.all().delete()

    def test_no_refund_settings_configured(self):
        booking = ServiceBookingFactory(amount_paid=Decimal("100.00"))
        result = calculate_service_refund_amount(booking)

        self.assertEqual(result["entitled_amount"], Decimal("0.00"))
        self.assertEqual(result["details"], "Refund settings not configured.")
        self.assertEqual(result["policy_applied"], "N/A")

    def test_online_deposit_full_refund_scenario(self):
        settings = RefundSettingsFactory(
            deposit_full_refund_days=7,
            deposit_partial_refund_days=3,
            deposit_no_refund_days=1
        )
        # Drop-off 8 days from now, cancellation is now
        dropoff_date = timezone.now().date() + timedelta(days=8)
        booking = ServiceBookingFactory(
            dropoff_date=dropoff_date,
            dropoff_time=time(9, 0),
            amount_paid=Decimal("100.00"),
            payment_method="online_deposit"
        )
        
        result = calculate_service_refund_amount(booking)

        self.assertEqual(result["entitled_amount"], Decimal("100.00"))
        self.assertIn("Full Deposit Refund", result["policy_applied"])

    def test_online_deposit_partial_refund_scenario(self):
        settings = RefundSettingsFactory(
            deposit_full_refund_days=7,
            deposit_partial_refund_days=3,
            deposit_no_refund_days=1,
            deposit_partial_refund_percentage=Decimal("50.00")
        )
        # Drop-off 5 days from now, cancellation is now
        dropoff_date = timezone.now().date() + timedelta(days=5)
        booking = ServiceBookingFactory(
            dropoff_date=dropoff_date,
            dropoff_time=time(9, 0),
            amount_paid=Decimal("100.00"),
            payment_method="online_deposit"
        )
        
        result = calculate_service_refund_amount(booking)

        self.assertEqual(result["entitled_amount"], Decimal("50.00"))
        self.assertIn("Partial Deposit Refund", result["policy_applied"])
        self.assertIn("50.00%", result["policy_applied"])

    def test_online_deposit_no_refund_scenario(self):
        settings = RefundSettingsFactory(
            deposit_full_refund_days=7,
            deposit_partial_refund_days=3,
            deposit_no_refund_days=1
        )
        # Drop-off 0 days from now (today), cancellation is now
        dropoff_date = timezone.now().date()
        booking = ServiceBookingFactory(
            dropoff_date=dropoff_date,
            dropoff_time=time(9, 0),
            amount_paid=Decimal("100.00"),
            payment_method="online_deposit"
        )
        
        result = calculate_service_refund_amount(booking)

        self.assertEqual(result["entitled_amount"], Decimal("0.00"))
        self.assertIn("No Deposit Refund", result["policy_applied"])

    def test_full_payment_full_refund_scenario(self):
        settings = RefundSettingsFactory(
            full_payment_full_refund_days=7,
            full_payment_partial_refund_days=3,
            full_payment_no_refund_percentage=1
        )
        # Drop-off 8 days from now, cancellation is now
        dropoff_date = timezone.now().date() + timedelta(days=8)
        booking = ServiceBookingFactory(
            dropoff_date=dropoff_date,
            dropoff_time=time(9, 0),
            amount_paid=Decimal("200.00"),
            payment_method="online_full"
        )
        
        result = calculate_service_refund_amount(booking)

        self.assertEqual(result["entitled_amount"], Decimal("200.00"))
        self.assertIn("Full Payment Refund", result["policy_applied"])

    def test_full_payment_partial_refund_scenario(self):
        settings = RefundSettingsFactory(
            full_payment_full_refund_days=7,
            full_payment_partial_refund_days=3,
            full_payment_no_refund_percentage=1,
            full_payment_partial_refund_percentage=Decimal("75.00")
        )
        # Drop-off 5 days from now, cancellation is now
        dropoff_date = timezone.now().date() + timedelta(days=5)
        booking = ServiceBookingFactory(
            dropoff_date=dropoff_date,
            dropoff_time=time(9, 0),
            amount_paid=Decimal("200.00"),
            payment_method="online_full"
        )
        
        result = calculate_service_refund_amount(booking)

        self.assertEqual(result["entitled_amount"], Decimal("150.00")) # 75% of 200
        self.assertIn("Partial Payment Refund", result["policy_applied"])
        self.assertIn("75.00%", result["policy_applied"])

    def test_full_payment_no_refund_scenario(self):
        settings = RefundSettingsFactory(
            full_payment_full_refund_days=7,
            full_payment_partial_refund_days=3,
            full_payment_no_refund_percentage=1
        )
        # Drop-off 0 days from now (today), cancellation is now
        dropoff_date = timezone.now().date()
        booking = ServiceBookingFactory(
            dropoff_date=dropoff_date,
            dropoff_time=time(9, 0),
            amount_paid=Decimal("200.00"),
            payment_method="online_full"
        )
        
        result = calculate_service_refund_amount(booking)

        self.assertEqual(result["entitled_amount"], Decimal("0.00"))
        self.assertIn("No Payment Refund", result["policy_applied"])

    def test_cancellation_datetime_parameter(self):
        settings = RefundSettingsFactory(
            deposit_full_refund_days=7,
            deposit_partial_refund_days=3,
            deposit_no_refund_days=1,
            deposit_partial_refund_percentage=Decimal("50.00")
        )
        # Booking drop-off is 10 days from now
        booking_dropoff_date = timezone.now().date() + timedelta(days=10)
        booking = ServiceBookingFactory(
            dropoff_date=booking_dropoff_date,
            dropoff_time=time(9, 0),
            amount_paid=Decimal("100.00"),
            payment_method="online_deposit"
        )
        
        # Simulate cancellation 5 days before drop-off
        cancellation_datetime = timezone.make_aware(
            datetime.combine(booking_dropoff_date - timedelta(days=5), time(8, 0))
        )
        result = calculate_service_refund_amount(booking, cancellation_datetime=cancellation_datetime)

        # This should fall into partial refund based on the 5-day difference
        self.assertEqual(result["entitled_amount"], Decimal("50.00"))
        self.assertIn("Partial Deposit Refund", result["policy_applied"])

    def test_entitled_amount_never_exceeds_total_paid(self):
        settings = RefundSettingsFactory(
            full_payment_full_refund_days=1,
            full_payment_partial_refund_days=1,
            full_payment_no_refund_percentage=1
        )
        # Drop-off 2 days from now, cancellation is now
        dropoff_date = timezone.now().date() + timedelta(days=2)
        booking = ServiceBookingFactory(
            dropoff_date=dropoff_date,
            dropoff_time=time(9, 0),
            amount_paid=Decimal("50.00"),
            payment_method="online_full"
        )
        
        result = calculate_service_refund_amount(booking)
        self.assertEqual(result["entitled_amount"], Decimal("50.00"))

    def test_entitled_amount_never_less_than_zero(self):
        settings = RefundSettingsFactory(
            full_payment_full_refund_days=7,
            full_payment_partial_refund_days=3,
            full_payment_no_refund_percentage=1
        )
        # Drop-off 0 days from now, cancellation is now
        dropoff_date = timezone.now().date()
        booking = ServiceBookingFactory(
            dropoff_date=dropoff_date,
            dropoff_time=time(9, 0),
            amount_paid=Decimal("100.00"),
            payment_method="online_full"
        )
        
        result = calculate_service_refund_amount(booking)
        self.assertEqual(result["entitled_amount"], Decimal("0.00"))

    def test_decimal_quantization(self):
        settings = RefundSettingsFactory(
            deposit_full_refund_days=7,
            deposit_partial_refund_days=3,
            deposit_no_refund_days=1,
            deposit_partial_refund_percentage=Decimal("33.33")
        )
        # Drop-off 5 days from now, cancellation is now
        dropoff_date = timezone.now().date() + timedelta(days=5)
        booking = ServiceBookingFactory(
            dropoff_date=dropoff_date,
            dropoff_time=time(9, 0),
            amount_paid=Decimal("100.00"),
            payment_method="online_deposit"
        )
        
        result = calculate_service_refund_amount(booking)
        self.assertEqual(result["entitled_amount"], Decimal("33.33"))
        self.assertEqual(result["entitled_amount"].as_tuple().exponent, -2) # Check for 2 decimal places

    def test_booking_amount_paid_is_none(self):
        settings = RefundSettingsFactory(
            deposit_full_refund_days=7,
            deposit_partial_refund_days=3,
            deposit_no_refund_days=1,
            deposit_partial_refund_percentage=Decimal("50.00")
        )
        dropoff_date = timezone.now().date() + timedelta(days=5)
        booking = ServiceBookingFactory(
            dropoff_date=dropoff_date,
            dropoff_time=time(9, 0),
            amount_paid=Decimal("0.00"), # Pass Decimal("0.00") instead of None
            payment_method="online_deposit"
        )
        
        result = calculate_service_refund_amount(booking)
        self.assertEqual(result["entitled_amount"], Decimal("0.00"))
        self.assertIn("Partial Deposit Refund", result["policy_applied"])
