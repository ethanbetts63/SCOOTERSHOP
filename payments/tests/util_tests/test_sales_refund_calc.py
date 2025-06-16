# payments/tests/util_tests/test_sales_refund_calc.py

from django.test import TestCase
from decimal import Decimal
from datetime import datetime, timedelta
from django.utils import timezone
from unittest.mock import MagicMock

# Import the function to be tested
from payments.utils.sales_refund_calc import calculate_sales_refund_amount

# Import factories for creating test data
from payments.tests.test_helpers.model_factories import SalesBookingFactory, PaymentFactory, RefundPolicySettingsFactory

class SalesRefundCalcTests(TestCase):
    """
    Tests for the calculate_sales_refund_amount function in payments.utils.sales_refund_calc.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up test data that will be used across all test methods in this class.
        We create a single RefundPolicySettings instance as it's a singleton,
        and define common refund policy snapshots for easier testing.
        """
        cls.refund_policy_settings = RefundPolicySettingsFactory()

        # Define common refund policy snapshots for sales-specific tests
        # Note: Decimal values need to be converted to strings for JSON serialization if stored in DB
        # For direct use in tests, keep as Decimal or convert as needed for snapshot.
        cls.full_refund_enabled_grace_period_policy = {
            'sales_enable_deposit_refund': True,
            'sales_enable_deposit_refund_grace_period': True,
            'sales_deposit_refund_grace_period_hours': 24, # 24 hours grace period
        }

        cls.full_refund_enabled_no_grace_period_policy = {
            'sales_enable_deposit_refund': True,
            'sales_enable_deposit_refund_grace_period': False,
            'sales_deposit_refund_grace_period_hours': 0, # Irrelevant when grace period is false
        }

        cls.no_refund_disabled_policy = {
            'sales_enable_deposit_refund': False,
            'sales_enable_deposit_refund_grace_period': True, # Irrelevant
            'sales_deposit_refund_grace_period_hours': 24,    # Irrelevant
        }

    def _create_booking_with_payment(self, amount_paid, created_at_offset_hours=0, refund_policy_snapshot=None):
        """
        Helper to create a SalesBooking and an associated Payment.
        `created_at_offset_hours`: How many hours in the past the booking was created.
        """
        # Create a Payment instance with the refund policy snapshot
        payment = PaymentFactory(amount=amount_paid, status='succeeded')
        if refund_policy_snapshot:
            # Convert Decimal values to strings for JSON serialization in the snapshot if they were Decimals
            processed_snapshot = {k: str(v) if isinstance(v, Decimal) else v for k, v in refund_policy_snapshot.items()}
            payment.refund_policy_snapshot = processed_snapshot
        else:
            payment.refund_policy_snapshot = {}
        payment.save()

        # Create a SalesBooking instance. The created_at will be set to timezone.now() by auto_now_add initially.
        booking = SalesBookingFactory(
            payment=payment,
            amount_paid=amount_paid,
            # Do NOT pass created_at here directly, as auto_now_add will override it.
            # booking_status and payment_status are fine as they don't have auto_now_add.
            booking_status='confirmed',
            payment_status='deposit_paid' if amount_paid > 0 else 'unpaid',
        )

        # Manually set created_at AFTER the object has been created by the factory and save it.
        # This overrides the auto_now_add value for testing purposes.
        booking.created_at = timezone.now() - timedelta(hours=created_at_offset_hours)
        booking.save()

        return booking, payment

    # --- Test Cases for Sales Refund Scenarios ---

    def test_full_refund_within_grace_period(self):
        """
        Tests full refund when deposit refunds are enabled, grace period is enabled,
        and cancellation occurs within the grace period.
        """
        # Booking created 12 hours ago, grace period is 24 hours
        booking, payment = self._create_booking_with_payment(
            amount_paid=Decimal('100.00'),
            created_at_offset_hours=12,
            refund_policy_snapshot=self.full_refund_enabled_grace_period_policy
        )
        cancellation_datetime = timezone.now() # Cancellation now

        result = calculate_sales_refund_amount(booking, payment.refund_policy_snapshot, cancellation_datetime)

        self.assertEqual(result['entitled_amount'], Decimal('100.00'))
        self.assertEqual(result['policy_applied'], "Full Refund Policy (Within 24 hour grace period)")
        self.assertAlmostEqual(result['time_since_booking_creation_hours'], 12.0, places=1)
        self.assertIn("Cancellation occurred 12.00 hours after booking creation.", result['details'])

    def test_no_refund_outside_grace_period(self):
        """
        Tests no refund when deposit refunds are enabled, grace period is enabled,
        but cancellation occurs outside the grace period.
        """
        # Booking created 30 hours ago, grace period is 24 hours
        booking, payment = self._create_booking_with_payment(
            amount_paid=Decimal('100.00'),
            created_at_offset_hours=30,
            refund_policy_snapshot=self.full_refund_enabled_grace_period_policy
        )
        cancellation_datetime = timezone.now()

        result = calculate_sales_refund_amount(booking, payment.refund_policy_snapshot, cancellation_datetime)

        self.assertEqual(result['entitled_amount'], Decimal('0.00'))
        self.assertEqual(result['policy_applied'], "No Refund Policy (Grace Period Expired)")
        self.assertAlmostEqual(result['time_since_booking_creation_hours'], 30.0, places=1)
        self.assertIn("Cancellation occurred 30.00 hours after booking creation.", result['details'])

    def test_full_refund_grace_period_disabled(self):
        """
        Tests full refund when deposit refunds are enabled but grace period is disabled.
        Should always result in a full refund.
        """
        # Booking created 50 hours ago, but grace period is disabled
        booking, payment = self._create_booking_with_payment(
            amount_paid=Decimal('100.00'),
            created_at_offset_hours=50,
            refund_policy_snapshot=self.full_refund_enabled_no_grace_period_policy
        )
        cancellation_datetime = timezone.now()

        result = calculate_sales_refund_amount(booking, payment.refund_policy_snapshot, cancellation_datetime)

        self.assertEqual(result['entitled_amount'], Decimal('100.00'))
        self.assertEqual(result['policy_applied'], "Full Refund Policy (Grace Period Disabled)")
        self.assertAlmostEqual(result['time_since_booking_creation_hours'], 50.0, places=1)
        self.assertIn("Cancellation occurred 50.00 hours after booking creation.", result['details'])

    def test_no_refund_deposit_refund_disabled(self):
        """
        Tests no refund when deposit refunds are entirely disabled.
        """
        # Booking created 10 hours ago, but deposit refunds are disabled
        booking, payment = self._create_booking_with_payment(
            amount_paid=Decimal('100.00'),
            created_at_offset_hours=10,
            refund_policy_snapshot=self.no_refund_disabled_policy
        )
        cancellation_datetime = timezone.now()

        result = calculate_sales_refund_amount(booking, payment.refund_policy_snapshot, cancellation_datetime)

        self.assertEqual(result['entitled_amount'], Decimal('0.00'))
        self.assertEqual(result['policy_applied'], "No Refund Policy (Refunds Disabled)")
        self.assertAlmostEqual(result['time_since_booking_creation_hours'], 10.0, places=1)
        self.assertIn("Cancellation occurred 10.00 hours after booking creation.", result['details'])

    def test_no_refund_policy_snapshot(self):
        """
        Tests behavior when refund_policy_snapshot is missing or empty.
        Should result in no refund and appropriate details.
        """
        booking, payment = self._create_booking_with_payment(
            amount_paid=Decimal('100.00'),
            refund_policy_snapshot={} # Empty snapshot
        )
        result = calculate_sales_refund_amount(booking, {}, timezone.now()) # Pass empty dict directly

        self.assertEqual(result['entitled_amount'], Decimal('0.00'))
        self.assertEqual(result['details'], "No refund policy snapshot available for this booking's payment.")
        self.assertEqual(result['policy_applied'], 'N/A')
        self.assertEqual(result['time_since_booking_creation_hours'], 'N/A')

    def test_zero_amount_paid(self):
        """
        Tests calculation when the amount paid for the booking is zero.
        Should always result in a zero refund.
        """
        booking, payment = self._create_booking_with_payment(
            amount_paid=Decimal('0.00'),
            created_at_offset_hours=1,
            refund_policy_snapshot=self.full_refund_enabled_grace_period_policy
        )
        cancellation_datetime = timezone.now()

        result = calculate_sales_refund_amount(booking, payment.refund_policy_snapshot, cancellation_datetime)

        self.assertEqual(result['entitled_amount'], Decimal('0.00'))
        self.assertIn("Calculated: 0.00.", result['details'])
        # Policy applied will depend on settings, but entitled_amount should be 0

    def test_custom_cancellation_datetime(self):
        """
        Tests that a custom cancellation_datetime is used correctly for time difference calculation.
        """
        # Booking created now (offset 0)
        booking, payment = self._create_booking_with_payment(
            amount_paid=Decimal('100.00'),
            created_at_offset_hours=0,
            refund_policy_snapshot=self.full_refund_enabled_grace_period_policy
        )

        # Set cancellation_datetime 25 hours after booking creation
        custom_cancellation_datetime = booking.created_at + timedelta(hours=25)

        result = calculate_sales_refund_amount(booking, payment.refund_policy_snapshot, custom_cancellation_datetime)

        # Expect no refund because 25 hours is outside the 24-hour grace period
        self.assertEqual(result['entitled_amount'], Decimal('0.00'))
        self.assertEqual(result['policy_applied'], "No Refund Policy (Grace Period Expired)")
        self.assertAlmostEqual(result['time_since_booking_creation_hours'], 25.0, places=1)
        self.assertIn("Cancellation occurred 25.00 hours after booking creation.", result['details'])

    def test_exact_grace_period_boundary(self):
        """
        Tests cancellation exactly on the grace period boundary (e.g., 24 hours exactly).
        Should still be a full refund as it's <= grace_period_hours.
        """
        policy = self.full_refund_enabled_grace_period_policy.copy()
        policy['sales_deposit_refund_grace_period_hours'] = 24

        booking, payment = self._create_booking_with_payment(
            amount_paid=Decimal('100.00'),
            created_at_offset_hours=0, # Created now for precise control
            refund_policy_snapshot=policy
        )
        # Cancellation exactly 24 hours after creation
        cancellation_datetime = booking.created_at + timedelta(hours=24)

        result = calculate_sales_refund_amount(booking, payment.refund_policy_snapshot, cancellation_datetime)

        self.assertEqual(result['entitled_amount'], Decimal('100.00'))
        self.assertEqual(result['policy_applied'], "Full Refund Policy (Within 24 hour grace period)")
        self.assertAlmostEqual(result['time_since_booking_creation_hours'], 24.0, places=1)
        self.assertIn("Cancellation occurred 24.00 hours after booking creation.", result['details'])

    def test_just_after_grace_period_boundary(self):
        """
        Tests cancellation just after the grace period boundary (e.g., 24 hours and 1 minute).
        Should result in no refund.
        """
        policy = self.full_refund_enabled_grace_period_policy.copy()
        policy['sales_deposit_refund_grace_period_hours'] = 24

        booking, payment = self._create_booking_with_payment(
            amount_paid=Decimal('100.00'),
            created_at_offset_hours=0,
            refund_policy_snapshot=policy
        )
        # Cancellation 24 hours and 1 minute after creation
        cancellation_datetime = booking.created_at + timedelta(hours=24, minutes=1)

        result = calculate_sales_refund_amount(booking, payment.refund_policy_snapshot, cancellation_datetime)

        self.assertEqual(result['entitled_amount'], Decimal('0.00'))
        self.assertEqual(result['policy_applied'], "No Refund Policy (Grace Period Expired)")
        # Time will be slightly over 24.0, e.g., 24.0166...
        self.assertTrue(result['time_since_booking_creation_hours'] > 24.0)
        self.assertIn("Cancellation occurred", result['details'])

    def test_negative_time_difference_cancellation_before_creation(self):
        """
        Tests the edge case where cancellation_datetime is before booking.created_at.
        Should result in a full refund as `time_since_booking_creation_hours` would be negative,
        satisfying `time_since_booking_creation_hours <= grace_period_hours`.
        The `max(Decimal('0.00'), ...)` line also handles ensuring the refund is not negative.
        """
        policy = self.full_refund_enabled_grace_period_policy.copy()
        policy['sales_deposit_refund_grace_period_hours'] = 24

        # For this test, we need `created_at` to be in the "future" relative to a base `timezone.now()`
        # used for `cancellation_datetime` in some tests, to ensure a negative difference.
        # However, the current _create_booking_with_payment sets created_at based on a past offset.
        # Let's adjust this test to explicitly set a created_at that is after cancellation_datetime.

        # Establish a fixed point in time for the test to control `created_at` and `cancellation_datetime`
        fixed_now = timezone.make_aware(datetime(2025, 1, 1, 10, 0, 0))

        # Booking created at fixed_now
        booking, payment = self._create_booking_with_payment(
            amount_paid=Decimal('100.00'),
            created_at_offset_hours=0, # This will make created_at close to the time of factory creation
            refund_policy_snapshot=policy
        )
        # Manually set booking.created_at to be later than cancellation_datetime
        booking.created_at = fixed_now + timedelta(hours=5) # Booking created 5 hours after our fixed_now
        booking.save()

        # Cancellation happens at fixed_now, which is before booking.created_at
        cancellation_datetime = fixed_now

        result = calculate_sales_refund_amount(booking, payment.refund_policy_snapshot, cancellation_datetime)

        self.assertEqual(result['entitled_amount'], Decimal('100.00'))
        self.assertEqual(result['policy_applied'], "Full Refund Policy (Within 24 hour grace period)")
        # The time_since_booking_creation_hours should be negative here
        self.assertLess(result['time_since_booking_creation_hours'], 0)
        self.assertIn("Cancellation occurred", result['details'])
