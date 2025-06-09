# payments/tests/util_tests/test_service_refund_calc.py

from django.test import TestCase
from decimal import Decimal
from datetime import datetime, date, time, timedelta
from django.utils import timezone
from unittest.mock import MagicMock

# Corrected Imports
from payments.utils.service_refund_calc import calculate_service_refund_amount
from payments.tests.test_helpers.model_factories import ServiceBookingFactory, PaymentFactory, RefundPolicySettingsFactory

class ServiceRefundCalcTests(TestCase):
    """
    Tests for the calculate_service_refund_amount function in payments.service_refund_calc.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up test data that will be used across all test methods in this class.
        We create a single RefundPolicySettings instance as it's a singleton.
        """
        cls.refund_policy_settings = RefundPolicySettingsFactory()

        # Define common refund policy snapshots for easier testing
        # Convert Decimal values to strings for JSON serialization
        # Note: Service refund policy uses 'cancellation_full_payment_' prefix, not 'cancellation_upfront_'
        cls.full_payment_policy_snapshot = {
            'deposit_enabled': False,
            'cancellation_full_payment_full_refund_days': 7,
            'cancellation_full_payment_partial_refund_days': 3,
            'cancellation_full_payment_partial_refund_percentage': str(Decimal('50.00')),
            'cancellation_full_payment_minimal_refund_days': 1,
            'cancellation_full_payment_minimal_refund_percentage': str(Decimal('10.00')),
        }

        cls.deposit_payment_policy_snapshot = {
            'deposit_enabled': True,
            'cancellation_deposit_full_refund_days': 10,
            'cancellation_deposit_partial_refund_days': 5,
            'cancellation_deposit_partial_refund_percentage': str(Decimal('75.00')),
            'cancellation_deposit_minimal_refund_days': 2,
            'cancellation_deposit_minimal_refund_percentage': str(Decimal('20.00')),
        }

    def _create_booking_with_payment(self, total_amount, payment_method, payment_status=None, dropoff_date_offset_days=10, refund_policy_snapshot=None):
        """
        Helper to create a ServiceBooking and an associated Payment (if needed for context, though service_refund_calc uses booking.amount_paid).
        """
        # Create a Payment instance (though calculate_service_refund_amount uses booking.amount_paid directly)
        payment = PaymentFactory(amount=total_amount, status='succeeded')

        # Attach the refund policy snapshot to the payment
        if refund_policy_snapshot:
            processed_snapshot = {k: str(v) if isinstance(v, Decimal) else v for k, v in refund_policy_snapshot.items()}
            payment.refund_policy_snapshot = processed_snapshot
        else:
            payment.refund_policy_snapshot = {}
        payment.save()

        # Create a ServiceBooking instance
        dropoff_date = timezone.now().date() + timedelta(days=dropoff_date_offset_days)
        dropoff_time = time(10, 0) # Fixed dropoff time for consistency

        booking = ServiceBookingFactory(
            payment=payment, # Link payment for completeness, though amount_paid is used
            payment_method=payment_method,
            payment_status=payment_status if payment_status else 'paid' if payment_method == 'online_full' else 'deposit_paid',
            calculated_total=total_amount, # Changed from total_price to calculated_total
            amount_paid=total_amount, # This is the key field for calculation
            dropoff_date=dropoff_date,
            dropoff_time=dropoff_time,
            estimated_pickup_date=dropoff_date + timedelta(days=1), # Changed from pickup_date to estimated_pickup_date
            booking_status='confirmed', # Changed from status to booking_status
        )

        return booking, payment


    # --- Test Cases for Full Payments (online_full) ---

    def test_full_refund_full_payment(self):
        """
        Tests full refund for a full payment service booking when cancelled well in advance.
        """
        cancellation_datetime = timezone.now()
        # Dropoff in 8 days, full refund policy threshold is 7 days
        booking, payment = self._create_booking_with_payment(
            total_amount=Decimal('500.00'),
            payment_method='online_full',
            dropoff_date_offset_days=9, # Adjusted for 8 full days
            refund_policy_snapshot=self.full_payment_policy_snapshot
        )

        result = calculate_service_refund_amount(booking, payment.refund_policy_snapshot, cancellation_datetime)

        self.assertEqual(result['entitled_amount'], Decimal('500.00'))
        self.assertEqual(result['policy_applied'], "Full Payment Policy: Full Refund Policy")
        self.assertIn("Cancellation 8 days before drop-off.", result['details'])
        self.assertEqual(result['days_before_dropoff'], 8)

    def test_partial_refund_full_payment(self):
        """
        Tests partial refund for a full payment service booking when cancelled within partial refund window.
        """
        cancellation_datetime = timezone.now()
        # Dropoff in 4 days, partial refund policy threshold is 3 days
        booking, payment = self._create_booking_with_payment(
            total_amount=Decimal('500.00'),
            payment_method='online_full',
            dropoff_date_offset_days=5, # Adjusted for 4 full days
            refund_policy_snapshot=self.full_payment_policy_snapshot
        )

        result = calculate_service_refund_amount(booking, payment.refund_policy_snapshot, cancellation_datetime)

        expected_refund = (Decimal('500.00') * Decimal('50.00')) / Decimal('100.00')
        self.assertEqual(result['entitled_amount'], expected_refund)
        self.assertEqual(result['policy_applied'], "Full Payment Policy: Partial Refund Policy (50.00%)")
        self.assertIn("Cancellation 4 days before drop-off.", result['details'])
        self.assertEqual(result['days_before_dropoff'], 4)

    def test_minimal_refund_full_payment(self):
        """
        Tests minimal refund for a full payment service booking when cancelled within minimal refund window.
        """
        cancellation_datetime = timezone.now()
        # Dropoff in 2 days, minimal refund policy threshold is 1 day
        booking, payment = self._create_booking_with_payment(
            total_amount=Decimal('500.00'),
            payment_method='online_full',
            dropoff_date_offset_days=3, # Adjusted for 2 full days
            refund_policy_snapshot=self.full_payment_policy_snapshot
        )

        result = calculate_service_refund_amount(booking, payment.refund_policy_snapshot, cancellation_datetime)

        expected_refund = (Decimal('500.00') * Decimal('10.00')) / Decimal('100.00')
        self.assertEqual(result['entitled_amount'], expected_refund)
        self.assertEqual(result['policy_applied'], "Full Payment Policy: Minimal Refund Policy (10.00%)")
        self.assertIn("Cancellation 2 days before drop-off.", result['details'])
        self.assertEqual(result['days_before_dropoff'], 2)

    def test_no_refund_full_payment_too_close(self):
        """
        Tests no refund for a full payment service booking when cancelled too close to drop-off.
        """
        cancellation_datetime = timezone.now()
        # Dropoff in 0 days (same day), minimal refund policy threshold is 1 day
        booking, payment = self._create_booking_with_payment(
            total_amount=Decimal('500.00'),
            payment_method='online_full',
            dropoff_date_offset_days=1, # Adjusted for 0 full days
            refund_policy_snapshot=self.full_payment_policy_snapshot
        )

        result = calculate_service_refund_amount(booking, payment.refund_policy_snapshot, cancellation_datetime)

        self.assertEqual(result['entitled_amount'], Decimal('0.00'))
        self.assertEqual(result['policy_applied'], "Full Payment Policy: No Refund Policy (Too close to drop-off or after drop-off)")
        self.assertIn("Cancellation 0 days before drop-off.", result['details'])
        self.assertEqual(result['days_before_dropoff'], 0)

    def test_no_refund_full_payment_after_dropoff(self):
        """
        Tests no refund for a full payment service booking when cancelled after the drop-off time.
        """
        dropoff_date = timezone.now().date() - timedelta(days=1)
        cancellation_datetime = timezone.now()

        booking, payment = self._create_booking_with_payment(
            total_amount=Decimal('500.00'),
            payment_method='online_full',
            dropoff_date_offset_days=-1, # Initial setup, will be overwritten
            refund_policy_snapshot=self.full_payment_policy_snapshot
        )
        booking.dropoff_date = dropoff_date
        booking.save()

        dropoff_datetime = timezone.make_aware(datetime.combine(booking.dropoff_date, booking.dropoff_time))
        time_difference = dropoff_datetime - cancellation_datetime
        days_in_advance = time_difference.days

        result = calculate_service_refund_amount(booking, payment.refund_policy_snapshot, cancellation_datetime)

        self.assertEqual(result['entitled_amount'], Decimal('0.00'))
        self.assertEqual(result['policy_applied'], "Full Payment Policy: No Refund Policy (Too close to drop-off or after drop-off)")
        self.assertIn(f"Cancellation {days_in_advance} days before drop-off.", result['details'])
        self.assertEqual(result['days_before_dropoff'], days_in_advance)


    # --- Test Cases for Deposit Payments (online_deposit) ---

    def test_full_refund_deposit_payment(self):
        """
        Tests full refund for a deposit payment service booking when cancelled well in advance.
        """
        cancellation_datetime = timezone.now()
        # Dropoff in 11 days, full refund policy threshold for deposit is 10 days
        booking, payment = self._create_booking_with_payment(
            total_amount=Decimal('100.00'),
            payment_method='online_deposit',
            payment_status='deposit_paid',
            dropoff_date_offset_days=12, # Adjusted for 11 full days
            refund_policy_snapshot=self.deposit_payment_policy_snapshot
        )

        result = calculate_service_refund_amount(booking, payment.refund_policy_snapshot, cancellation_datetime)

        self.assertEqual(result['entitled_amount'], Decimal('100.00'))
        self.assertEqual(result['policy_applied'], "Deposit Payment Policy: Full Refund Policy")
        self.assertIn("Cancellation 11 days before drop-off.", result['details'])
        self.assertEqual(result['days_before_dropoff'], 11)

    def test_partial_refund_deposit_payment(self):
        """
        Tests partial refund for a deposit payment service booking when cancelled within partial refund window.
        """
        cancellation_datetime = timezone.now()
        # Dropoff in 6 days, partial refund policy threshold for deposit is 5 days
        booking, payment = self._create_booking_with_payment(
            total_amount=Decimal('100.00'),
            payment_method='online_deposit',
            payment_status='deposit_paid',
            dropoff_date_offset_days=7, # Adjusted for 6 full days
            refund_policy_snapshot=self.deposit_payment_policy_snapshot
        )

        result = calculate_service_refund_amount(booking, payment.refund_policy_snapshot, cancellation_datetime)

        expected_refund = (Decimal('100.00') * Decimal('75.00')) / Decimal('100.00')
        self.assertEqual(result['entitled_amount'], expected_refund)
        self.assertEqual(result['policy_applied'], "Deposit Payment Policy: Partial Refund Policy (75.00%)")
        self.assertIn("Cancellation 6 days before drop-off.", result['details'])
        self.assertEqual(result['days_before_dropoff'], 6)

    def test_minimal_refund_deposit_payment(self):
        """
        Tests minimal refund for a deposit payment service booking when cancelled within minimal refund window.
        """
        cancellation_datetime = timezone.now()
        # Dropoff in 3 days, minimal refund policy threshold for deposit is 2 days
        booking, payment = self._create_booking_with_payment(
            total_amount=Decimal('100.00'),
            payment_method='online_deposit',
            payment_status='deposit_paid',
            dropoff_date_offset_days=4, # Adjusted for 3 full days
            refund_policy_snapshot=self.deposit_payment_policy_snapshot
        )

        result = calculate_service_refund_amount(booking, payment.refund_policy_snapshot, cancellation_datetime)

        expected_refund = (Decimal('100.00') * Decimal('20.00')) / Decimal('100.00')
        self.assertEqual(result['entitled_amount'], expected_refund)
        self.assertEqual(result['policy_applied'], "Deposit Payment Policy: Minimal Refund Policy (20.00%)")
        self.assertIn("Cancellation 3 days before drop-off.", result['details'])
        self.assertEqual(result['days_before_dropoff'], 3)

    def test_no_refund_deposit_payment_too_close(self):
        """
        Tests no refund for a deposit payment service booking when cancelled too close to drop-off.
        """
        cancellation_datetime = timezone.now()
        # Dropoff in 1 day, minimal refund policy threshold for deposit is 2 days
        booking, payment = self._create_booking_with_payment(
            total_amount=Decimal('100.00'),
            payment_method='online_deposit',
            payment_status='deposit_paid',
            dropoff_date_offset_days=2, # Adjusted for 1 full day
            refund_policy_snapshot=self.deposit_payment_policy_snapshot
        )

        result = calculate_service_refund_amount(booking, payment.refund_policy_snapshot, cancellation_datetime)

        self.assertEqual(result['entitled_amount'], Decimal('0.00'))
        self.assertEqual(result['policy_applied'], "Deposit Payment Policy: No Refund Policy (Too close to drop-off or after drop-off)")
        self.assertIn("Cancellation 1 days before drop-off.", result['details'])
        self.assertEqual(result['days_before_dropoff'], 1)


    # --- Edge Cases and Other Scenarios ---

    def test_no_refund_policy_snapshot(self):
        """
        Tests behavior when refund_policy_snapshot is missing or empty.
        """
        booking, payment = self._create_booking_with_payment(
            total_amount=Decimal('500.00'),
            payment_method='online_full',
            refund_policy_snapshot={}
        )
        result = calculate_service_refund_amount(booking, payment.refund_policy_snapshot, timezone.now())

        self.assertEqual(result['entitled_amount'], Decimal('0.00'))
        self.assertEqual(result['details'], "No refund policy snapshot available for this booking's payment.")
        self.assertEqual(result['policy_applied'], 'N/A')
        self.assertEqual(result['days_before_dropoff'], 'N/A')

    def test_manual_payment_method(self):
        """
        Tests behavior for payment methods that require manual refunds.
        """
        cancellation_datetime = timezone.now()
        booking, payment = self._create_booking_with_payment(
            total_amount=Decimal('500.00'),
            payment_method='bank_transfer',
            dropoff_date_offset_days=5,
            refund_policy_snapshot=self.full_payment_policy_snapshot
        )

        result = calculate_service_refund_amount(booking, payment.refund_policy_snapshot, cancellation_datetime)

        self.assertEqual(result['entitled_amount'], Decimal('0.00'))
        self.assertIn("No Refund Policy: Refund for 'bank_transfer' payment method is handled manually.", result['details'])
        self.assertEqual(result['policy_applied'], "Manual Refund Policy for bank_transfer")
        self.assertEqual(result['days_before_dropoff'], 'N/A')

    def test_booking_without_payment_object_amount_paid_used(self):
        """
        Tests the case where a service booking's amount_paid is used directly.
        """
        cancellation_datetime = timezone.now()

        mock_booking = MagicMock()
        mock_booking.payment = None # No payment object linked
        mock_booking.amount_paid = Decimal('250.00') # Explicitly set amount_paid
        mock_booking.payment_method = 'online_full'
        mock_booking.payment_status = 'paid'
        mock_booking.dropoff_date = timezone.now().date() + timedelta(days=9) # Adjusted for 8 full days
        mock_booking.dropoff_time = time(10, 0)
        mock_booking.get_payment_method_display.return_value = 'Online Full'

        result = calculate_service_refund_amount(mock_booking, self.full_payment_policy_snapshot, cancellation_datetime)

        self.assertEqual(result['entitled_amount'], Decimal('250.00'))
        self.assertIn("250.00 (100.00% of 250.00).", result['details'])
        self.assertIn("Cancellation 8 days before drop-off.", result['details'])

    def test_booking_without_payment_object_zero_amount_paid(self):
        """
        Tests the case where a service booking might not have a linked payment object
        and amount_paid is zero.
        """
        cancellation_datetime = timezone.now()

        mock_booking = MagicMock()
        mock_booking.payment = None # No payment object linked
        mock_booking.amount_paid = Decimal('0.00') # Explicitly set amount_paid to zero
        mock_booking.payment_method = 'online_full'
        mock_booking.payment_status = 'paid'
        mock_booking.dropoff_date = timezone.now().date() + timedelta(days=9) # Adjusted for 8 full days
        mock_booking.dropoff_time = time(10, 0)
        mock_booking.get_payment_method_display.return_value = 'Online Full'

        result = calculate_service_refund_amount(mock_booking, self.full_payment_policy_snapshot, cancellation_datetime)

        self.assertEqual(result['entitled_amount'], Decimal('0.00'))
        self.assertIn("0.00 (100.00% of 0.00).", result['details'])
        self.assertIn("Cancellation 8 days before drop-off.", result['details'])

    def test_custom_cancellation_datetime(self):
        """
        Tests that a custom cancellation_datetime is used correctly.
        """
        booking, payment = self._create_booking_with_payment(
            total_amount=Decimal('500.00'),
            payment_method='online_full',
            dropoff_date_offset_days=11, # To ensure 10 full days difference
            refund_policy_snapshot=self.full_payment_policy_snapshot
        )

        dropoff_datetime = timezone.make_aware(datetime.combine(booking.dropoff_date, booking.dropoff_time))
        custom_cancellation_datetime = dropoff_datetime - timedelta(days=8, minutes=1) # Exactly 8 full days before

        result = calculate_service_refund_amount(booking, payment.refund_policy_snapshot, custom_cancellation_datetime)

        self.assertEqual(result['entitled_amount'], Decimal('500.00'))
        self.assertEqual(result['policy_applied'], "Full Payment Policy: Full Refund Policy")
        self.assertEqual(result['days_before_dropoff'], 8)

    def test_exact_boundary_full_refund_days(self):
        """
        Tests cancellation exactly on the boundary for full refund.
        Should result in a full refund.
        """
        cancellation_datetime = timezone.make_aware(datetime.combine(date(2025, 1, 1), time(10, 0, 0)))
        dropoff_datetime_exact_boundary = cancellation_datetime + timedelta(days=7)

        booking, payment = self._create_booking_with_payment(
            total_amount=Decimal('500.00'),
            payment_method='online_full',
            dropoff_date_offset_days=0, # Overwritten
            refund_policy_snapshot=self.full_payment_policy_snapshot
        )
        booking.dropoff_date = dropoff_datetime_exact_boundary.date()
        booking.dropoff_time = dropoff_datetime_exact_boundary.time()
        booking.save()

        result = calculate_service_refund_amount(booking, payment.refund_policy_snapshot, cancellation_datetime)
        self.assertEqual(result['entitled_amount'], Decimal('500.00'))
        self.assertEqual(result['policy_applied'], "Full Payment Policy: Full Refund Policy")
        self.assertEqual(result['days_before_dropoff'], 7)

    def test_just_under_boundary_full_refund_days(self):
        """
        Tests cancellation just under the boundary for full refund.
        Should result in a partial refund.
        """
        cancellation_datetime = timezone.make_aware(datetime.combine(date(2025, 1, 1), time(10, 0, 0)))
        dropoff_datetime_just_under = cancellation_datetime + timedelta(days=6, hours=23)

        booking, payment = self._create_booking_with_payment(
            total_amount=Decimal('500.00'),
            payment_method='online_full',
            dropoff_date_offset_days=0, # Overwritten
            refund_policy_snapshot=self.full_payment_policy_snapshot
        )
        booking.dropoff_date = dropoff_datetime_just_under.date()
        booking.dropoff_time = dropoff_datetime_just_under.time()
        booking.save()

        result = calculate_service_refund_amount(booking, payment.refund_policy_snapshot, cancellation_datetime)
        expected_refund = (Decimal('500.00') * Decimal('50.00')) / Decimal('100.00')
        self.assertEqual(result['entitled_amount'], expected_refund)
        self.assertEqual(result['policy_applied'], "Full Payment Policy: Partial Refund Policy (50.00%)")
        self.assertEqual(result['days_before_dropoff'], 6)

    def test_minimal_refund_zero_percentage(self):
        """
        Tests a scenario where minimal refund percentage is 0%.
        """
        policy_with_zero_minimal = self.full_payment_policy_snapshot.copy()
        policy_with_zero_minimal['cancellation_full_payment_minimal_refund_percentage'] = str(Decimal('0.00'))

        cancellation_datetime = timezone.now()
        booking, payment = self._create_booking_with_payment(
            total_amount=Decimal('500.00'),
            payment_method='online_full',
            dropoff_date_offset_days=2, # Adjusted for 1 full day
            refund_policy_snapshot=policy_with_zero_minimal
        )

        result = calculate_service_refund_amount(booking, payment.refund_policy_snapshot, cancellation_datetime)
        self.assertEqual(result['entitled_amount'], Decimal('0.00'))
        self.assertEqual(result['policy_applied'], "Full Payment Policy: Minimal Refund Policy (0.00%)")
        self.assertEqual(result['days_before_dropoff'], 1)

    def test_decimal_precision(self):
        """
        Ensures Decimal objects are handled correctly for precision.
        """
        policy_snapshot = {
            'deposit_enabled': False,
            'cancellation_full_payment_full_refund_days': 7,
            'cancellation_full_payment_partial_refund_days': 3,
            'cancellation_full_payment_partial_refund_percentage': str(Decimal('33.33')),
            'cancellation_full_payment_minimal_refund_days': 1,
            'cancellation_full_payment_minimal_refund_percentage': str(Decimal('0.00')),
        }

        cancellation_datetime = timezone.now()
        booking, payment = self._create_booking_with_payment(
            total_amount=Decimal('100.00'),
            payment_method='online_full',
            dropoff_date_offset_days=5, # Adjusted for 4 full days
            refund_policy_snapshot=policy_snapshot
        )

        result = calculate_service_refund_amount(booking, payment.refund_policy_snapshot, cancellation_datetime)
        self.assertEqual(result['entitled_amount'], Decimal('33.33'))
        self.assertEqual(result['policy_applied'], "Full Payment Policy: Partial Refund Policy (33.33%)")
        self.assertEqual(result['days_before_dropoff'], 4)

    def test_total_paid_for_calculation_from_amount_paid(self):
        """
        Ensures total_paid_for_calculation correctly uses booking.amount_paid.
        """
        cancellation_datetime = timezone.now()
        booking, payment = self._create_booking_with_payment(
            total_amount=Decimal('123.45'),
            payment_method='online_full',
            dropoff_date_offset_days=9, # Adjusted for 8 full days
            refund_policy_snapshot=self.full_payment_policy_snapshot
        )

        result = calculate_service_refund_amount(booking, payment.refund_policy_snapshot, cancellation_datetime)

        self.assertEqual(result['entitled_amount'], Decimal('123.45'))
        self.assertIn("123.45 (100.00% of 123.45).", result['details'])

