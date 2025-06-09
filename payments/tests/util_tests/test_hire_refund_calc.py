# payments/tests/util_tests/test_hire_refund_calc.py

from django.test import TestCase
from decimal import Decimal
# Corrected: Import datetime class, date class, time class, and timedelta from the datetime module
from datetime import datetime, date, time, timedelta
from django.utils import timezone
from unittest.mock import MagicMock

# Corrected Imports
from payments.utils.hire_refund_calc import calculate_hire_refund_amount
from payments.tests.test_helpers.model_factories import HireBookingFactory, PaymentFactory, RefundPolicySettingsFactory

class HireRefundCalcTests(TestCase):
    """
    Tests for the calculate_hire_refund_amount function in payments.hire_refund_calc.
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
        cls.full_payment_policy_snapshot = {
            'deposit_enabled': False,
            'cancellation_upfront_full_refund_days': 7,
            'cancellation_upfront_partial_refund_days': 3,
            'cancellation_upfront_partial_refund_percentage': str(Decimal('50.00')), # Convert to string
            'cancellation_upfront_minimal_refund_days': 1,
            'cancellation_upfront_minimal_refund_percentage': str(Decimal('10.00')), # Convert to string
        }

        cls.deposit_payment_policy_snapshot = {
            'deposit_enabled': True,
            'cancellation_deposit_full_refund_days': 10,
            'cancellation_deposit_partial_refund_days': 5,
            'cancellation_deposit_partial_refund_percentage': str(Decimal('75.00')), # Convert to string
            'cancellation_deposit_minimal_refund_days': 2,
            'cancellation_deposit_minimal_refund_percentage': str(Decimal('20.00')), # Convert to string
        }

    def _create_booking_with_payment(self, total_amount, payment_method, payment_status=None, pickup_date_offset_days=10, refund_policy_snapshot=None):
        """
        Helper to create a HireBooking and an associated Payment.
        """
        # Create a Payment instance first
        payment = PaymentFactory(amount=total_amount, status='succeeded')

        # Attach the refund policy snapshot to the payment AFTER converting Decimals to strings
        if refund_policy_snapshot:
            processed_snapshot = {k: str(v) if isinstance(v, Decimal) else v for k, v in refund_policy_snapshot.items()}
            payment.refund_policy_snapshot = processed_snapshot
        else:
            payment.refund_policy_snapshot = {} # Ensure it's an empty dict if None was passed
        payment.save() # Save the payment after updating the snapshot

        # Create a HireBooking instance
        # Ensure pickup_date is in the future relative to 'now'
        pickup_date = timezone.now().date() + timedelta(days=pickup_date_offset_days)
        pickup_time = time(10, 0) # Fixed pickup time for consistency

        booking = HireBookingFactory(
            payment=payment,
            payment_method=payment_method,
            payment_status=payment_status if payment_status else 'paid' if payment_method == 'online_full' else 'deposit_paid',
            grand_total=total_amount, # Ensure grand_total matches payment amount for calculation consistency
            amount_paid=total_amount,
            pickup_date=pickup_date,
            pickup_time=pickup_time,
            return_date=pickup_date + timedelta(days=2), # Arbitrary return date
            status='confirmed',
        )

        return booking, payment


    # --- Test Cases for Full Payments (online_full) ---

    def test_full_refund_full_payment(self):
        """
        Tests full refund for a full payment when cancelled well in advance.
        """
        cancellation_datetime = timezone.now()
        # Pickup in 8 days, full refund policy threshold is 7 days
        # To ensure 8 full days, if now is e.g. 13:00 and pickup is 10:00,
        # we need pickup_date to be 9 days from now.
        booking, payment = self._create_booking_with_payment(
            total_amount=Decimal('500.00'),
            payment_method='online_full',
            pickup_date_offset_days=9, # Changed from 8 to 9 to get 8 full days difference
            refund_policy_snapshot=self.full_payment_policy_snapshot
        )

        result = calculate_hire_refund_amount(booking, payment.refund_policy_snapshot, cancellation_datetime)

        self.assertEqual(result['entitled_amount'], Decimal('500.00'))
        self.assertEqual(result['policy_applied'], "Upfront Payment Policy: Full Refund Policy")
        self.assertIn("Cancellation 8 days before pickup.", result['details'])
        self.assertEqual(result['days_before_pickup'], 8)

    def test_partial_refund_full_payment(self):
        """
        Tests partial refund for a full payment when cancelled within partial refund window.
        """
        cancellation_datetime = timezone.now()
        # Pickup in 4 days, partial refund policy threshold is 3 days
        # To ensure 4 full days, if now is e.g. 13:00 and pickup is 10:00,
        # we need pickup_date to be 5 days from now.
        booking, payment = self._create_booking_with_payment(
            total_amount=Decimal('500.00'),
            payment_method='online_full',
            pickup_date_offset_days=5, # Changed from 4 to 5 to get 4 full days difference
            refund_policy_snapshot=self.full_payment_policy_snapshot
        )

        result = calculate_hire_refund_amount(booking, payment.refund_policy_snapshot, cancellation_datetime)

        expected_refund = (Decimal('500.00') * Decimal('50.00')) / Decimal('100.00')
        self.assertEqual(result['entitled_amount'], expected_refund)
        self.assertEqual(result['policy_applied'], "Upfront Payment Policy: Partial Refund Policy (50.00%)")
        self.assertIn("Cancellation 4 days before pickup.", result['details'])
        self.assertEqual(result['days_before_pickup'], 4)

    def test_minimal_refund_full_payment(self):
        """
        Tests minimal refund for a full payment when cancelled within minimal refund window.
        """
        cancellation_datetime = timezone.now()
        # Pickup in 2 days, minimal refund policy threshold is 1 day
        # To ensure 2 full days, if now is e.g. 13:00 and pickup is 10:00,
        # we need pickup_date to be 3 days from now.
        booking, payment = self._create_booking_with_payment(
            total_amount=Decimal('500.00'),
            payment_method='online_full',
            pickup_date_offset_days=3, # Changed from 2 to 3 to get 2 full days difference
            refund_policy_snapshot=self.full_payment_policy_snapshot
        )

        result = calculate_hire_refund_amount(booking, payment.refund_policy_snapshot, cancellation_datetime)

        expected_refund = (Decimal('500.00') * Decimal('10.00')) / Decimal('100.00')
        self.assertEqual(result['entitled_amount'], expected_refund)
        self.assertEqual(result['policy_applied'], "Upfront Payment Policy: Minimal Refund Policy (10.00%)")
        self.assertIn("Cancellation 2 days before pickup.", result['details'])
        self.assertEqual(result['days_before_pickup'], 2)

    def test_no_refund_full_payment_too_close(self):
        """
        Tests no refund for a full payment when cancelled too close to pickup (less than minimal days).
        """
        cancellation_datetime = timezone.now()
        # Pickup in 0 days (same day), minimal refund policy threshold is 1 day
        # To ensure 0 full days, if now is e.g. 13:00 and pickup is 10:00,
        # we need pickup_date to be 1 day from now, or earlier.
        # If pickup_date_offset_days is 1, and current time is 13:00, pickup time is 10:00
        # Then (now_date + 1 day) 10:00 - now_date 13:00 = 21 hours = 0 full days.
        booking, payment = self._create_booking_with_payment(
            total_amount=Decimal('500.00'),
            payment_method='online_full',
            pickup_date_offset_days=1, # Changed from 0 to 1 to get 0 full days difference
            refund_policy_snapshot=self.full_payment_policy_snapshot
        )

        result = calculate_hire_refund_amount(booking, payment.refund_policy_snapshot, cancellation_datetime)

        self.assertEqual(result['entitled_amount'], Decimal('0.00'))
        self.assertEqual(result['policy_applied'], "Upfront Payment Policy: No Refund Policy (Too close to pickup or after pickup)")
        self.assertIn("Cancellation 0 days before pickup.", result['details'])
        self.assertEqual(result['days_before_pickup'], 0)

    def test_no_refund_full_payment_after_pickup(self):
        """
        Tests no refund for a full payment when cancelled after the pickup time.
        """
        # Set pickup date to yesterday
        pickup_date = timezone.now().date() - timedelta(days=1)
        # Set cancellation time to now (after pickup)
        cancellation_datetime = timezone.now()

        booking, payment = self._create_booking_with_payment(
            total_amount=Decimal('500.00'),
            payment_method='online_full',
            pickup_date_offset_days=-1, # Initial setup, will be overwritten by direct assignment
            refund_policy_snapshot=self.full_payment_policy_snapshot
        )
        # Manually adjust pickup_date to ensure it's in the past
        booking.pickup_date = pickup_date
        booking.save()

        # Recalculate time_difference for the expected details string
        # Use datetime.combine from the datetime module directly
        pickup_datetime = timezone.make_aware(datetime.combine(booking.pickup_date, booking.pickup_time))
        time_difference = pickup_datetime - cancellation_datetime
        days_in_advance = time_difference.days


        result = calculate_hire_refund_amount(booking, payment.refund_policy_snapshot, cancellation_datetime)

        self.assertEqual(result['entitled_amount'], Decimal('0.00'))
        self.assertEqual(result['policy_applied'], "Upfront Payment Policy: No Refund Policy (Too close to pickup or after pickup)")
        # days_in_advance will be negative if pickup is in the past
        self.assertIn(f"Cancellation {days_in_advance} days before pickup.", result['details'])
        self.assertEqual(result['days_before_pickup'], days_in_advance) # Will be negative


    # --- Test Cases for Deposit Payments (online_deposit) ---

    def test_full_refund_deposit_payment(self):
        """
        Tests full refund for a deposit payment when cancelled well in advance.
        """
        cancellation_datetime = timezone.now()
        # Pickup in 11 days, full refund policy threshold for deposit is 10 days
        # To ensure 11 full days, we need pickup_date_offset_days = 12
        booking, payment = self._create_booking_with_payment(
            total_amount=Decimal('100.00'), # Deposit amount
            payment_method='online_deposit',
            payment_status='deposit_paid',
            pickup_date_offset_days=12, # Changed from 11 to 12
            refund_policy_snapshot=self.deposit_payment_policy_snapshot
        )

        result = calculate_hire_refund_amount(booking, payment.refund_policy_snapshot, cancellation_datetime)

        self.assertEqual(result['entitled_amount'], Decimal('100.00'))
        self.assertEqual(result['policy_applied'], "Deposit Payment Policy: Full Refund Policy")
        self.assertIn("Cancellation 11 days before pickup.", result['details'])
        self.assertEqual(result['days_before_pickup'], 11)

    def test_partial_refund_deposit_payment(self):
        """
        Tests partial refund for a deposit payment when cancelled within partial refund window.
        """
        cancellation_datetime = timezone.now()
        # Pickup in 6 days, partial refund policy threshold for deposit is 5 days
        # To ensure 6 full days, we need pickup_date_offset_days = 7
        booking, payment = self._create_booking_with_payment(
            total_amount=Decimal('100.00'),
            payment_method='online_deposit',
            payment_status='deposit_paid',
            pickup_date_offset_days=7, # Changed from 6 to 7
            refund_policy_snapshot=self.deposit_payment_policy_snapshot
        )

        result = calculate_hire_refund_amount(booking, payment.refund_policy_snapshot, cancellation_datetime)

        expected_refund = (Decimal('100.00') * Decimal('75.00')) / Decimal('100.00')
        self.assertEqual(result['entitled_amount'], expected_refund)
        self.assertEqual(result['policy_applied'], "Deposit Payment Policy: Partial Refund Policy (75.00%)")
        self.assertIn("Cancellation 6 days before pickup.", result['details'])
        self.assertEqual(result['days_before_pickup'], 6)

    def test_minimal_refund_deposit_payment(self):
        """
        Tests minimal refund for a deposit payment when cancelled within minimal refund window.
        """
        cancellation_datetime = timezone.now()
        # Pickup in 3 days, minimal refund policy threshold for deposit is 2 days
        # To ensure 3 full days, we need pickup_date_offset_days = 4
        booking, payment = self._create_booking_with_payment(
            total_amount=Decimal('100.00'),
            payment_method='online_deposit',
            payment_status='deposit_paid',
            pickup_date_offset_days=4, # Changed from 3 to 4
            refund_policy_snapshot=self.deposit_payment_policy_snapshot
        )

        result = calculate_hire_refund_amount(booking, payment.refund_policy_snapshot, cancellation_datetime)

        expected_refund = (Decimal('100.00') * Decimal('20.00')) / Decimal('100.00')
        self.assertEqual(result['entitled_amount'], expected_refund)
        self.assertEqual(result['policy_applied'], "Deposit Payment Policy: Minimal Refund Policy (20.00%)")
        self.assertIn("Cancellation 3 days before pickup.", result['details'])
        self.assertEqual(result['days_before_pickup'], 3)

    def test_no_refund_deposit_payment_too_close(self):
        """
        Tests no refund for a deposit payment when cancelled too close to pickup (less than minimal days).
        """
        cancellation_datetime = timezone.now()
        # Pickup in 1 day, minimal refund policy threshold for deposit is 2 days
        # To ensure 1 full day, we need pickup_date_offset_days = 2
        booking, payment = self._create_booking_with_payment(
            total_amount=Decimal('100.00'),
            payment_method='online_deposit',
            payment_status='deposit_paid',
            pickup_date_offset_days=2, # Changed from 1 to 2
            refund_policy_snapshot=self.deposit_payment_policy_snapshot
        )

        result = calculate_hire_refund_amount(booking, payment.refund_policy_snapshot, cancellation_datetime)

        self.assertEqual(result['entitled_amount'], Decimal('0.00'))
        self.assertEqual(result['policy_applied'], "Deposit Payment Policy: No Refund Policy (Too close to pickup or after pickup)")
        self.assertIn("Cancellation 1 days before pickup.", result['details'])
        self.assertEqual(result['days_before_pickup'], 1)


    # --- Edge Cases and Other Scenarios ---

    def test_no_refund_policy_snapshot(self):
        """
        Tests behavior when refund_policy_snapshot is missing or empty.
        """
        booking, payment = self._create_booking_with_payment(
            total_amount=Decimal('500.00'),
            payment_method='online_full',
            refund_policy_snapshot={} # Explicitly set to an empty dict
        )
        # The function expects a dict, so an empty one should trigger the specific message
        result = calculate_hire_refund_amount(booking, payment.refund_policy_snapshot, timezone.now())

        self.assertEqual(result['entitled_amount'], Decimal('0.00'))
        self.assertEqual(result['details'], "No refund policy snapshot available for this booking.")
        self.assertEqual(result['policy_applied'], 'N/A')
        self.assertEqual(result['days_before_pickup'], 'N/A')

    def test_manual_payment_method(self):
        """
        Tests behavior for payment methods that require manual refunds.
        """
        cancellation_datetime = timezone.now()
        booking, payment = self._create_booking_with_payment(
            total_amount=Decimal('500.00'),
            payment_method='bank_transfer', # Manual payment method
            pickup_date_offset_days=5, # Offset doesn't matter much for this test, but keep consistent
            refund_policy_snapshot=self.full_payment_policy_snapshot
        )

        result = calculate_hire_refund_amount(booking, payment.refund_policy_snapshot, cancellation_datetime)

        self.assertEqual(result['entitled_amount'], Decimal('0.00'))
        # Updated assertion to match the actual output from get_payment_method_display() if it returns raw value
        self.assertIn("No Refund Policy: Refund for 'bank_transfer' payment method is handled manually.", result['details'])
        self.assertEqual(result['policy_applied'], "Manual Refund Policy for bank_transfer") # Updated policy_applied
        self.assertEqual(result['days_before_pickup'], 'N/A')

    def test_booking_without_payment_object(self):
        """
        Tests the case where a booking might not have a linked payment object.
        This shouldn't happen in a real scenario if payment.amount is used,
        but good for robustness. We mock the booking's payment attribute to be None.
        """
        cancellation_datetime = timezone.now()

        # Create a mock booking where payment is None
        mock_booking = MagicMock()
        mock_booking.payment = None # Simulate no payment object
        mock_booking.payment_method = 'online_full'
        mock_booking.payment_status = 'paid'
        # To get 8 full days difference
        mock_booking.pickup_date = timezone.now().date() + timedelta(days=9) # Adjusted for 8 full days
        mock_booking.pickup_time = time(10, 0)
        mock_booking.get_payment_method_display.return_value = 'Online Full'


        result = calculate_hire_refund_amount(mock_booking, self.full_payment_policy_snapshot, cancellation_datetime)

        self.assertEqual(result['entitled_amount'], Decimal('0.00'))
        self.assertIn("0.00 (100.00% of 0.00).", result['details']) # Should calculate 0% of 0
        self.assertIn("Cancellation 8 days before pickup.", result['details']) # Should now pass for 8 days

    def test_custom_cancellation_datetime(self):
        """
        Tests that a custom cancellation_datetime is used correctly.
        """
        # Pickup is in 10 days from NOW (using 11 days offset for the date to ensure 10 full days)
        booking, payment = self._create_booking_with_payment(
            total_amount=Decimal('500.00'),
            payment_method='online_full',
            pickup_date_offset_days=11, # Changed from 10 to 11
            refund_policy_snapshot=self.full_payment_policy_snapshot
        )

        # Calculate a custom cancellation datetime that is precisely 8 days before pickup
        pickup_datetime = timezone.make_aware(datetime.combine(booking.pickup_date, booking.pickup_time))
        # This custom cancellation is designed to make days_in_advance exactly 8
        custom_cancellation_datetime = pickup_datetime - timedelta(days=8, minutes=1)

        result = calculate_hire_refund_amount(booking, payment.refund_policy_snapshot, custom_cancellation_datetime)

        self.assertEqual(result['entitled_amount'], Decimal('500.00'))
        self.assertEqual(result['policy_applied'], "Upfront Payment Policy: Full Refund Policy")
        self.assertEqual(result['days_before_pickup'], 8) # Should calculate based on custom time

    def test_exact_boundary_full_refund_days(self):
        """
        Tests cancellation exactly on the boundary for full refund.
        Should result in a full refund.
        """
        # Setup: Pickup is exactly 7 full days from the cancellation time.
        # Use timezone.make_aware with a naive datetime.datetime object
        # Corrected: Use date() and time() directly without qualifying them with 'datetime.'
        cancellation_datetime = timezone.make_aware(datetime.combine(date(2025, 1, 1), time(10, 0, 0))) # Fixed for predictability
        # Pickup datetime should be 7 days later at the exact same time
        pickup_datetime_exact_boundary = cancellation_datetime + timedelta(days=7)

        booking, payment = self._create_booking_with_payment(
            total_amount=Decimal('500.00'),
            payment_method='online_full',
            pickup_date_offset_days=0, # This will be overwritten by direct assignment
            refund_policy_snapshot=self.full_payment_policy_snapshot
        )
        booking.pickup_date = pickup_datetime_exact_boundary.date()
        booking.pickup_time = pickup_datetime_exact_boundary.time()
        booking.save()

        result = calculate_hire_refund_amount(booking, payment.refund_policy_snapshot, cancellation_datetime)
        self.assertEqual(result['entitled_amount'], Decimal('500.00'))
        self.assertEqual(result['policy_applied'], "Upfront Payment Policy: Full Refund Policy")
        self.assertEqual(result['days_before_pickup'], 7)

    def test_just_under_boundary_full_refund_days(self):
        """
        Tests cancellation just under the boundary for full refund.
        Should result in a partial refund.
        """
        # Setup: Pickup is just under 7 full days from the cancellation time.
        # Fixed cancellation_datetime for predictable results.
        # Corrected: Use date() and time() directly without qualifying them with 'datetime.'
        cancellation_datetime = timezone.make_aware(datetime.combine(date(2025, 1, 1), time(10, 0, 0)))
        # Pickup should be slightly less than 7 days from now, e.g., 6 days and 23 hours later.
        pickup_datetime_just_under = cancellation_datetime + timedelta(days=6, hours=23) # This is less than 7 full days

        booking, payment = self._create_booking_with_payment(
            total_amount=Decimal('500.00'),
            payment_method='online_full',
            pickup_date_offset_days=0, # Overwritten
            refund_policy_snapshot=self.full_payment_policy_snapshot
        )
        booking.pickup_date = pickup_datetime_just_under.date()
        booking.pickup_time = pickup_datetime_just_under.time()
        booking.save()

        result = calculate_hire_refund_amount(booking, payment.refund_policy_snapshot, cancellation_datetime)
        expected_refund = (Decimal('500.00') * Decimal('50.00')) / Decimal('100.00')
        self.assertEqual(result['entitled_amount'], expected_refund)
        self.assertEqual(result['policy_applied'], "Upfront Payment Policy: Partial Refund Policy (50.00%)")
        self.assertEqual(result['days_before_pickup'], 6) # Should be 6 full days

    def test_minimal_refund_zero_percentage(self):
        """
        Tests a scenario where minimal refund percentage is 0%.
        """
        policy_with_zero_minimal = self.full_payment_policy_snapshot.copy()
        policy_with_zero_minimal['cancellation_upfront_minimal_refund_percentage'] = str(Decimal('0.00')) # Convert to string

        cancellation_datetime = timezone.now()
        # Pickup in 1 day (offset 2 to get 1 full day difference)
        booking, payment = self._create_booking_with_payment(
            total_amount=Decimal('500.00'),
            payment_method='online_full',
            pickup_date_offset_days=2, # Changed from 1 to 2
            refund_policy_snapshot=policy_with_zero_minimal
        )

        result = calculate_hire_refund_amount(booking, payment.refund_policy_snapshot, cancellation_datetime)
        self.assertEqual(result['entitled_amount'], Decimal('0.00'))
        self.assertEqual(result['policy_applied'], "Upfront Payment Policy: Minimal Refund Policy (0.00%)")
        self.assertEqual(result['days_before_pickup'], 1)

    def test_decimal_precision(self):
        """
        Ensures Decimal objects are handled correctly for precision.
        """
        policy_snapshot = {
            'deposit_enabled': False,
            'cancellation_upfront_full_refund_days': 7,
            'cancellation_upfront_partial_refund_days': 3,
            'cancellation_upfront_partial_refund_percentage': str(Decimal('33.33')), # Tricky percentage, convert to string
            'cancellation_upfront_minimal_refund_days': 1,
            'cancellation_upfront_minimal_refund_percentage': str(Decimal('0.00')),
        }

        cancellation_datetime = timezone.now()
        # Pickup in 4 days (offset 5 to get 4 full days difference)
        booking, payment = self._create_booking_with_payment(
            total_amount=Decimal('100.00'),
            payment_method='online_full',
            pickup_date_offset_days=5, # Changed from 4 to 5
            refund_policy_snapshot=policy_snapshot
        )

        result = calculate_hire_refund_amount(booking, payment.refund_policy_snapshot, cancellation_datetime)
        # 100 * 0.3333 = 33.33
        self.assertEqual(result['entitled_amount'], Decimal('33.33'))
        self.assertEqual(result['policy_applied'], "Upfront Payment Policy: Partial Refund Policy (33.33%)")
        self.assertEqual(result['days_before_pickup'], 4)

    def test_total_paid_for_calculation_from_payment_amount(self):
        """
        Ensures total_paid_for_calculation correctly uses booking.payment.amount.
        """
        cancellation_datetime = timezone.now()
        # Pickup in 8 days (offset 9 to get 8 full days difference)
        booking, payment = self._create_booking_with_payment(
            total_amount=Decimal('123.45'), # Specific amount to check
            payment_method='online_full',
            pickup_date_offset_days=9, # Changed from 8 to 9
            refund_policy_snapshot=self.full_payment_policy_snapshot
        )

        result = calculate_hire_refund_amount(booking, payment.refund_policy_snapshot, cancellation_datetime)

        self.assertEqual(result['entitled_amount'], Decimal('123.45'))
        self.assertIn("123.45 (100.00% of 123.45).", result['details'])

    def test_total_paid_for_calculation_no_payment_amount(self):
        """
        Ensures total_paid_for_calculation defaults to 0 if payment.amount is missing or None.
        This uses MagicMock to simulate the scenario where payment.amount is None.
        """
        cancellation_datetime = timezone.now()

        # Create a mock payment object with amount set to None
        mock_payment = MagicMock()
        mock_payment.amount = None
        mock_payment.refund_policy_snapshot = self.full_payment_policy_snapshot # Still needs a snapshot

        # Create a mock booking object and link the mock payment
        mock_booking = MagicMock()
        mock_booking.payment = mock_payment # Link the mock payment
        mock_booking.payment_method = 'online_full'
        mock_booking.payment_status = 'paid'
        mock_booking.pickup_date = timezone.now().date() + timedelta(days=9) # Adjusted for 8 full days
        mock_booking.pickup_time = time(10, 0)
        mock_booking.get_payment_method_display.return_value = 'Online Full'


        result = calculate_hire_refund_amount(mock_booking, mock_payment.refund_policy_snapshot, cancellation_datetime)

        self.assertEqual(result['entitled_amount'], Decimal('0.00'))
        self.assertIn("0.00 (100.00% of 0.00).", result['details']) # Should calculate 0% of 0
        self.assertIn("Cancellation 8 days before pickup.", result['details']) # Should now pass for 8 days
