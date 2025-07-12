from django.test import TestCase
from decimal import Decimal
from datetime import datetime, date, time, timedelta
from django.utils import timezone
from unittest.mock import MagicMock


from refunds.utils.service_refund_calc import calculate_service_refund_amount
from payments.tests.test_helpers.model_factories import (
    ServiceBookingFactory,
    PaymentFactory,
    RefundSettingsFactory,
)


class ServiceRefundCalcTests(TestCase):

    @classmethod
    def setUpTestData(cls):

        cls.refund_policy_settings = RefundSettingsFactory()

        cls.full_payment_policy_snapshot = {
            "deposit_enabled": False,
            "full_payment_full_refund_days": 7,
            "full_payment_partial_refund_days": 3,
            "full_payment_partial_refund_percentage": str(
                Decimal("50.00")
            ),
            "full_payment_no_refund_percentage": 1,

        }

        cls.deposit_payment_policy_snapshot = {
            "deposit_enabled": True,
            "cancellation_deposit_full_refund_days": 10,
            "cancellation_deposit_partial_refund_days": 5,
            "cancellation_deposit_partial_refund_percentage": str(Decimal("75.00")),
            "cancellation_deposit_minimal_refund_days": 2,
        }

    def _create_booking_with_payment(
        self,
        total_amount,
        payment_method,
        payment_status=None,
        dropoff_date_offset_days=10,
        refund_policy_snapshot=None,
    ):

        payment = PaymentFactory(amount=total_amount, status="succeeded")

        if refund_policy_snapshot:
            processed_snapshot = {
                k: str(v) if isinstance(v, Decimal) else v
                for k, v in refund_policy_snapshot.items()
            }
            payment.refund_policy_snapshot = processed_snapshot
        else:
            payment.refund_policy_snapshot = {}
        payment.save()

        dropoff_date = timezone.now().date() + timedelta(days=dropoff_date_offset_days)
        dropoff_time = time(10, 0)

        booking = ServiceBookingFactory(
            payment=payment,
            payment_method=payment_method,
            payment_status=(
                payment_status
                if payment_status
                else "paid" if payment_method == "online_full" else "deposit_paid"
            ),
            calculated_total=total_amount,
            amount_paid=total_amount,
            dropoff_date=dropoff_date,
            dropoff_time=dropoff_time,
            estimated_pickup_date=dropoff_date + timedelta(days=1),
            booking_status="confirmed",
        )

        return booking, payment

    def test_full_refund_full_payment(self):

        cancellation_datetime = timezone.now()

        booking, payment = self._create_booking_with_payment(
            total_amount=Decimal("500.00"),
            payment_method="online_full",
            dropoff_date_offset_days=9,
            refund_policy_snapshot=self.full_payment_policy_snapshot,
        )

        result = calculate_service_refund_amount(
            booking, payment.refund_policy_snapshot, cancellation_datetime
        )

        self.assertEqual(result["entitled_amount"], Decimal("500.00"))
        self.assertEqual(
            result["policy_applied"], "Full Payment Policy: Full Refund Policy"
        )
        self.assertIn("Cancellation 8 days before drop-off.", result["details"])
        self.assertEqual(result["days_before_dropoff"], 8)

    def test_partial_refund_full_payment(self):

        cancellation_datetime = timezone.now()

        booking, payment = self._create_booking_with_payment(
            total_amount=Decimal("500.00"),
            payment_method="online_full",
            dropoff_date_offset_days=5,
            refund_policy_snapshot=self.full_payment_policy_snapshot,
        )

        result = calculate_service_refund_amount(
            booking, payment.refund_policy_snapshot, cancellation_datetime
        )

        expected_refund = (Decimal("500.00") * Decimal("50.00")) / Decimal("100.00")
        self.assertEqual(result["entitled_amount"], expected_refund)
        self.assertEqual(
            result["policy_applied"],
            "Full Payment Policy: Partial Refund Policy (50.00%)",
        )
        self.assertIn("Cancellation 4 days before drop-off.", result["details"])
        self.assertEqual(result["days_before_dropoff"], 4)

    def test_minimal_refund_full_payment(self):

        cancellation_datetime = timezone.now()

        booking, payment = self._create_booking_with_payment(
            total_amount=Decimal("500.00"),
            payment_method="online_full",
            dropoff_date_offset_days=3,
            refund_policy_snapshot=self.full_payment_policy_snapshot,
        )

        result = calculate_service_refund_amount(
            booking, payment.refund_policy_snapshot, cancellation_datetime
        )

        expected_refund = (Decimal("500.00") * Decimal("10.00")) / Decimal("100.00")
        self.assertEqual(result["entitled_amount"], expected_refund)
        self.assertEqual(
            result["policy_applied"],
            "Full Payment Policy: Minimal Refund Policy (10.00%)",
        )
        self.assertIn("Cancellation 2 days before drop-off.", result["details"])
        self.assertEqual(result["days_before_dropoff"], 2)

    def test_no_refund_full_payment_too_close(self):

        cancellation_datetime = timezone.now()

        booking, payment = self._create_booking_with_payment(
            total_amount=Decimal("500.00"),
            payment_method="online_full",
            dropoff_date_offset_days=1,
            refund_policy_snapshot=self.full_payment_policy_snapshot,
        )

        result = calculate_service_refund_amount(
            booking, payment.refund_policy_snapshot, cancellation_datetime
        )

        self.assertEqual(result["entitled_amount"], Decimal("0.00"))
        self.assertEqual(
            result["policy_applied"],
            "Full Payment Policy: No Refund Policy (Too close to drop-off or after drop-off)",
        )
        self.assertIn("Cancellation 0 days before drop-off.", result["details"])
        self.assertEqual(result["days_before_dropoff"], 0)

    def test_no_refund_full_payment_after_dropoff(self):

        dropoff_date = timezone.now().date() - timedelta(days=1)
        cancellation_datetime = timezone.now()

        booking, payment = self._create_booking_with_payment(
            total_amount=Decimal("500.00"),
            payment_method="online_full",
            dropoff_date_offset_days=-1,
            refund_policy_snapshot=self.full_payment_policy_snapshot,
        )
        booking.dropoff_date = dropoff_date
        booking.save()

        dropoff_datetime = timezone.make_aware(
            datetime.combine(booking.dropoff_date, booking.dropoff_time)
        )
        time_difference = dropoff_datetime - cancellation_datetime
        days_in_advance = time_difference.days

        result = calculate_service_refund_amount(
            booking, payment.refund_policy_snapshot, cancellation_datetime
        )

        self.assertEqual(result["entitled_amount"], Decimal("0.00"))
        self.assertEqual(
            result["policy_applied"],
            "Full Payment Policy: No Refund Policy (Too close to drop-off or after drop-off)",
        )
        self.assertIn(
            f"Cancellation {days_in_advance} days before drop-off.", result["details"]
        )
        self.assertEqual(result["days_before_dropoff"], days_in_advance)

    def test_full_refund_deposit_payment(self):

        cancellation_datetime = timezone.now()

        booking, payment = self._create_booking_with_payment(
            total_amount=Decimal("100.00"),
            payment_method="online_deposit",
            payment_status="deposit_paid",
            dropoff_date_offset_days=12,
            refund_policy_snapshot=self.deposit_payment_policy_snapshot,
        )

        result = calculate_service_refund_amount(
            booking, payment.refund_policy_snapshot, cancellation_datetime
        )

        self.assertEqual(result["entitled_amount"], Decimal("100.00"))
        self.assertEqual(
            result["policy_applied"], "Deposit Payment Policy: Full Refund Policy"
        )
        self.assertIn("Cancellation 11 days before drop-off.", result["details"])
        self.assertEqual(result["days_before_dropoff"], 11)

    def test_partial_refund_deposit_payment(self):

        cancellation_datetime = timezone.now()

        booking, payment = self._create_booking_with_payment(
            total_amount=Decimal("100.00"),
            payment_method="online_deposit",
            payment_status="deposit_paid",
            dropoff_date_offset_days=7,
            refund_policy_snapshot=self.deposit_payment_policy_snapshot,
        )

        result = calculate_service_refund_amount(
            booking, payment.refund_policy_snapshot, cancellation_datetime
        )

        expected_refund = (Decimal("100.00") * Decimal("75.00")) / Decimal("100.00")
        self.assertEqual(result["entitled_amount"], expected_refund)
        self.assertEqual(
            result["policy_applied"],
            "Deposit Payment Policy: Partial Refund Policy (75.00%)",
        )
        self.assertIn("Cancellation 6 days before drop-off.", result["details"])
        self.assertEqual(result["days_before_dropoff"], 6)

    def test_minimal_refund_deposit_payment(self):

        cancellation_datetime = timezone.now()

        booking, payment = self._create_booking_with_payment(
            total_amount=Decimal("100.00"),
            payment_method="online_deposit",
            payment_status="deposit_paid",
            dropoff_date_offset_days=4,
            refund_policy_snapshot=self.deposit_payment_policy_snapshot,
        )

        result = calculate_service_refund_amount(
            booking, payment.refund_policy_snapshot, cancellation_datetime
        )

        expected_refund = (Decimal("100.00") * Decimal("20.00")) / Decimal("100.00")
        self.assertEqual(result["entitled_amount"], expected_refund)
        self.assertEqual(
            result["policy_applied"],
            "Deposit Payment Policy: Minimal Refund Policy (20.00%)",
        )
        self.assertIn("Cancellation 3 days before drop-off.", result["details"])
        self.assertEqual(result["days_before_dropoff"], 3)

    def test_no_refund_deposit_payment_too_close(self):

        cancellation_datetime = timezone.now()

        booking, payment = self._create_booking_with_payment(
            total_amount=Decimal("100.00"),
            payment_method="online_deposit",
            payment_status="deposit_paid",
            dropoff_date_offset_days=2,
            refund_policy_snapshot=self.deposit_payment_policy_snapshot,
        )

        result = calculate_service_refund_amount(
            booking, payment.refund_policy_snapshot, cancellation_datetime
        )

        self.assertEqual(result["entitled_amount"], Decimal("0.00"))
        self.assertEqual(
            result["policy_applied"],
            "Deposit Payment Policy: No Refund Policy (Too close to drop-off or after drop-off)",
        )
        self.assertIn("Cancellation 1 days before drop-off.", result["details"])
        self.assertEqual(result["days_before_dropoff"], 1)

    def test_no_refund_policy_snapshot(self):

        booking, payment = self._create_booking_with_payment(
            total_amount=Decimal("500.00"),
            payment_method="online_full",
            refund_policy_snapshot={},
        )
        result = calculate_service_refund_amount(
            booking, payment.refund_policy_snapshot, timezone.now()
        )

        self.assertEqual(result["entitled_amount"], Decimal("0.00"))
        self.assertEqual(
            result["details"],
            "No refund policy snapshot available for this booking's payment.",
        )
        self.assertEqual(result["policy_applied"], "N/A")
        self.assertEqual(result["days_before_dropoff"], "N/A")

    def test_manual_payment_method(self):

        cancellation_datetime = timezone.now()
        booking, payment = self._create_booking_with_payment(
            total_amount=Decimal("500.00"),
            payment_method="bank_transfer",
            dropoff_date_offset_days=5,
            refund_policy_snapshot=self.full_payment_policy_snapshot,
        )

        result = calculate_service_refund_amount(
            booking, payment.refund_policy_snapshot, cancellation_datetime
        )

        self.assertEqual(result["entitled_amount"], Decimal("0.00"))
        self.assertIn(
            "No Refund Policy: Refund for 'bank_transfer' payment method is handled manually.",
            result["details"],
        )
        self.assertEqual(
            result["policy_applied"], "Manual Refund Policy for bank_transfer"
        )
        self.assertEqual(result["days_before_dropoff"], "N/A")

    def test_booking_without_payment_object_amount_paid_used(self):

        cancellation_datetime = timezone.now()

        mock_booking = MagicMock()
        mock_booking.payment = None
        mock_booking.amount_paid = Decimal("250.00")
        mock_booking.payment_method = "online_full"
        mock_booking.payment_status = "paid"
        mock_booking.dropoff_date = timezone.now().date() + timedelta(days=9)
        mock_booking.dropoff_time = time(10, 0)
        mock_booking.get_payment_method_display.return_value = "Online Full"

        result = calculate_service_refund_amount(
            mock_booking, self.full_payment_policy_snapshot, cancellation_datetime
        )

        self.assertEqual(result["entitled_amount"], Decimal("250.00"))
        self.assertIn("250.00 (100.00% of 250.00).", result["details"])
        self.assertIn("Cancellation 8 days before drop-off.", result["details"])

    def test_booking_without_payment_object_zero_amount_paid(self):

        cancellation_datetime = timezone.now()

        mock_booking = MagicMock()
        mock_booking.payment = None
        mock_booking.amount_paid = Decimal("0.00")
        mock_booking.payment_method = "online_full"
        mock_booking.payment_status = "paid"
        mock_booking.dropoff_date = timezone.now().date() + timedelta(days=9)
        mock_booking.dropoff_time = time(10, 0)
        mock_booking.get_payment_method_display.return_value = "Online Full"

        result = calculate_service_refund_amount(
            mock_booking, self.full_payment_policy_snapshot, cancellation_datetime
        )

        self.assertEqual(result["entitled_amount"], Decimal("0.00"))
        self.assertIn("0.00 (100.00% of 0.00).", result["details"])
        self.assertIn("Cancellation 8 days before drop-off.", result["details"])

    def test_custom_cancellation_datetime(self):

        booking, payment = self._create_booking_with_payment(
            total_amount=Decimal("500.00"),
            payment_method="online_full",
            dropoff_date_offset_days=11,
            refund_policy_snapshot=self.full_payment_policy_snapshot,
        )

        dropoff_datetime = timezone.make_aware(
            datetime.combine(booking.dropoff_date, booking.dropoff_time)
        )
        custom_cancellation_datetime = dropoff_datetime - timedelta(days=8, minutes=1)

        result = calculate_service_refund_amount(
            booking, payment.refund_policy_snapshot, custom_cancellation_datetime
        )

        self.assertEqual(result["entitled_amount"], Decimal("500.00"))
        self.assertEqual(
            result["policy_applied"], "Full Payment Policy: Full Refund Policy"
        )
        self.assertEqual(result["days_before_dropoff"], 8)

    def test_exact_boundary_full_refund_days(self):

        cancellation_datetime = timezone.make_aware(
            datetime.combine(date(2025, 1, 1), time(10, 0, 0))
        )
        dropoff_datetime_exact_boundary = cancellation_datetime + timedelta(days=7)

        booking, payment = self._create_booking_with_payment(
            total_amount=Decimal("500.00"),
            payment_method="online_full",
            dropoff_date_offset_days=0,
            refund_policy_snapshot=self.full_payment_policy_snapshot,
        )
        booking.dropoff_date = dropoff_datetime_exact_boundary.date()
        booking.dropoff_time = dropoff_datetime_exact_boundary.time()
        booking.save()

        result = calculate_service_refund_amount(
            booking, payment.refund_policy_snapshot, cancellation_datetime
        )
        self.assertEqual(result["entitled_amount"], Decimal("500.00"))
        self.assertEqual(
            result["policy_applied"], "Full Payment Policy: Full Refund Policy"
        )
        self.assertEqual(result["days_before_dropoff"], 7)

    def test_just_under_boundary_full_refund_days(self):

        cancellation_datetime = timezone.make_aware(
            datetime.combine(date(2025, 1, 1), time(10, 0, 0))
        )
        dropoff_datetime_just_under = cancellation_datetime + timedelta(
            days=6, hours=23
        )

        booking, payment = self._create_booking_with_payment(
            total_amount=Decimal("500.00"),
            payment_method="online_full",
            dropoff_date_offset_days=0,
            refund_policy_snapshot=self.full_payment_policy_snapshot,
        )
        booking.dropoff_date = dropoff_datetime_just_under.date()
        booking.dropoff_time = dropoff_datetime_just_under.time()
        booking.save()

        result = calculate_service_refund_amount(
            booking, payment.refund_policy_snapshot, cancellation_datetime
        )
        expected_refund = (Decimal("500.00") * Decimal("50.00")) / Decimal("100.00")
        self.assertEqual(result["entitled_amount"], expected_refund)
        self.assertEqual(
            result["policy_applied"],
            "Full Payment Policy: Partial Refund Policy (50.00%)",
        )
        self.assertEqual(result["days_before_dropoff"], 6)

    def test_minimal_refund_zero_percentage(self):

        policy_with_zero_minimal = self.full_payment_policy_snapshot.copy()

        cancellation_datetime = timezone.now()
        booking, payment = self._create_booking_with_payment(
            total_amount=Decimal("500.00"),
            payment_method="online_full",
            dropoff_date_offset_days=2,
            refund_policy_snapshot=policy_with_zero_minimal,
        )

        result = calculate_service_refund_amount(
            booking, payment.refund_policy_snapshot, cancellation_datetime
        )
        self.assertEqual(result["entitled_amount"], Decimal("0.00"))
        self.assertEqual(
            result["policy_applied"],
            "Full Payment Policy: Minimal Refund Policy (0.00%)",
        )
        self.assertEqual(result["days_before_dropoff"], 1)

    def test_decimal_precision(self):

        policy_snapshot = {
            "deposit_enabled": False,
            "full_payment_full_refund_days": 7,
            "full_payment_partial_refund_days": 3,
            "full_payment_partial_refund_percentage": str(
                Decimal("33.33")
            ),
            "full_payment_no_refund_percentage": 1,
            "cancellation_full_payment_minimal_refund_percentage": str(Decimal("0.00")),
        }

        cancellation_datetime = timezone.now()
        booking, payment = self._create_booking_with_payment(
            total_amount=Decimal("100.00"),
            payment_method="online_full",
            dropoff_date_offset_days=5,
            refund_policy_snapshot=policy_snapshot,
        )

        result = calculate_service_refund_amount(
            booking, payment.refund_policy_snapshot, cancellation_datetime
        )
        self.assertEqual(result["entitled_amount"], Decimal("33.33"))
        self.assertEqual(
            result["policy_applied"],
            "Full Payment Policy: Partial Refund Policy (33.33%)",
        )
        self.assertEqual(result["days_before_dropoff"], 4)

    def test_total_paid_for_calculation_from_amount_paid(self):

        cancellation_datetime = timezone.now()
        booking, payment = self._create_booking_with_payment(
            total_amount=Decimal("123.45"),
            payment_method="online_full",
            dropoff_date_offset_days=9,
            refund_policy_snapshot=self.full_payment_policy_snapshot,
        )

        result = calculate_service_refund_amount(
            booking, payment.refund_policy_snapshot, cancellation_datetime
        )

        self.assertEqual(result["entitled_amount"], Decimal("123.45"))
        self.assertIn("123.45 (100.00% of 123.45).", result["details"])
