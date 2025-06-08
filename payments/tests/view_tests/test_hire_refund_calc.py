# payments/tests/test_hire_refund_calc.py

from django.test import TestCase
from decimal import Decimal
from django.utils import timezone
import datetime

# Import the function to be tested
from payments.utils.hire_refund_calc import calculate_hire_refund_amount

# Import model factories for creating test data
from hire.tests.test_helpers.model_factories import (
    create_hire_booking,
    create_hire_settings,
    create_payment,
    create_driver_profile,
)
from dashboard.models import HireSettings # Import HireSettings directly for deletion in tests

class HireRefundCalcTests(TestCase):
    """
    Tests for the calculate_hire_refund_amount function in payments/hire_refund_calc.py.
    """

    def setUp(self):
        """
        Set up common test data for all tests.
        Ensure a clean slate for HireSettings for each test to avoid interference.
        """
        # Delete any existing HireSettings to ensure a fresh one is created for each test
        HireSettings.objects.all().delete()

        # Create a default HireSettings instance for consistent policy definitions
        self.hire_settings = create_hire_settings(
            # Upfront payment policy
            cancellation_upfront_full_refund_days=7,
            cancellation_upfront_partial_refund_days=3,
            cancellation_upfront_partial_refund_percentage=Decimal('50.00'),
            cancellation_upfront_minimal_refund_days=1,
            cancellation_upfront_minimal_refund_percentage=Decimal('0.00'),
            # Deposit payment policy
            cancellation_deposit_full_refund_days=14, # Longer for deposit to differentiate
            cancellation_deposit_partial_refund_days=7,
            cancellation_deposit_partial_refund_percentage=Decimal('75.00'), # Different percentage
            cancellation_deposit_minimal_refund_days=3,
            cancellation_deposit_minimal_refund_percentage=Decimal('25.00'), # Different percentage
            deposit_enabled=True, # Enable deposit for testing deposit scenarios
            default_deposit_calculation_method='fixed_amount',
            deposit_amount=Decimal('50.00'), # Default deposit amount in settings
        )

        # Create a driver profile
        self.driver_profile = create_driver_profile()

        # Define a base pickup datetime for consistent testing
        self.base_pickup_date = timezone.now().date() + datetime.timedelta(days=30)
        self.base_pickup_time = datetime.time(10, 0)
        self.base_pickup_datetime = timezone.make_aware(
            datetime.datetime.combine(self.base_pickup_date, self.base_pickup_time)
        )

        # Create a refund policy snapshot from the current hire settings for use in payments
        self.refund_policy_snapshot = {
            'cancellation_upfront_full_refund_days': self.hire_settings.cancellation_upfront_full_refund_days,
            'cancellation_upfront_partial_refund_days': self.hire_settings.cancellation_upfront_partial_refund_days,
            'cancellation_upfront_partial_refund_percentage': str(self.hire_settings.cancellation_upfront_partial_refund_percentage),
            'cancellation_upfront_minimal_refund_days': self.hire_settings.cancellation_upfront_minimal_refund_days,
            'cancellation_upfront_minimal_refund_percentage': str(self.hire_settings.cancellation_upfront_minimal_refund_percentage),
            'cancellation_deposit_full_refund_days': self.hire_settings.cancellation_deposit_full_refund_days,
            'cancellation_deposit_partial_refund_days': self.hire_settings.cancellation_deposit_partial_refund_days,
            'cancellation_deposit_partial_refund_percentage': str(self.hire_settings.cancellation_deposit_partial_refund_percentage),
            'cancellation_deposit_minimal_refund_days': self.hire_settings.cancellation_deposit_minimal_refund_days,
            'cancellation_deposit_minimal_refund_percentage': str(self.hire_settings.cancellation_deposit_minimal_refund_percentage),
            'deposit_enabled': self.hire_settings.deposit_enabled,
            'default_deposit_calculation_method': self.hire_settings.default_deposit_calculation_method,
            'deposit_percentage': str(self.hire_settings.deposit_percentage),
            'deposit_amount': str(self.hire_settings.deposit_amount),
        }


    # --- Test Cases for Upfront Payments ---

    def test_upfront_full_refund(self):
        """
        Test full refund for upfront payment when cancelled well in advance.
        """
        # Create a fully paid booking
        payment = create_payment(
            amount=Decimal('500.00'),
            status='paid',
            driver_profile=self.driver_profile,
            stripe_payment_intent_id='pi_upfront_full_refund',
            refund_policy_snapshot=self.refund_policy_snapshot # Pass the snapshot
        )
        hire_booking = create_hire_booking(
            driver_profile=self.driver_profile,
            payment=payment,
            amount_paid=payment.amount,
            grand_total=payment.amount,
            payment_status='paid',
            status='confirmed',
            pickup_date=self.base_pickup_date,
            pickup_time=self.base_pickup_time,
            payment_method='online_full',
        )
        # No need to save payment again as it's linked during hire_booking creation

        # Cancel 8 days before pickup (full refund threshold is 7 days)
        cancellation_datetime = self.base_pickup_datetime - datetime.timedelta(days=8, hours=1)
        # Pass the refund_policy_snapshot from the payment object
        results = calculate_hire_refund_amount(hire_booking, hire_booking.payment.refund_policy_snapshot, cancellation_datetime)

        self.assertEqual(results['entitled_amount'], Decimal('500.00'))
        self.assertIn("Upfront Payment Policy: Full Refund Policy", results['details'])
        self.assertEqual(results['days_before_pickup'], 8)

    def test_upfront_partial_refund(self):
        """
        Test partial refund for upfront payment when cancelled within the partial window.
        """
        payment = create_payment(
            amount=Decimal('500.00'),
            status='paid',
            driver_profile=self.driver_profile,
            refund_policy_snapshot=self.refund_policy_snapshot # Pass the snapshot
        )
        hire_booking = create_hire_booking(
            driver_profile=self.driver_profile,
            payment=payment,
            amount_paid=payment.amount,
            grand_total=payment.amount,
            payment_status='paid',
            status='confirmed',
            pickup_date=self.base_pickup_date,
            pickup_time=self.base_pickup_time,
            payment_method='online_full',
        )

        # Cancel 4 days before pickup (partial refund threshold is 3 days, full is 7 days)
        cancellation_datetime = self.base_pickup_datetime - datetime.timedelta(days=4, hours=1)
        results = calculate_hire_refund_amount(hire_booking, hire_booking.payment.refund_policy_snapshot, cancellation_datetime)

        expected_refund = (Decimal('500.00') * Decimal('50.00')) / Decimal('100.00')
        self.assertEqual(results['entitled_amount'], expected_refund)
        self.assertIn("Upfront Payment Policy: Partial Refund Policy (50.00%)", results['details'])
        self.assertEqual(results['days_before_pickup'], 4)

    def test_upfront_minimal_refund(self):
        """
        Test minimal refund for upfront payment when cancelled within the minimal window.
        """
        payment = create_payment(
            amount=Decimal('500.00'),
            status='paid',
            driver_profile=self.driver_profile,
            refund_policy_snapshot=self.refund_policy_snapshot # Pass the snapshot
        )
        hire_booking = create_hire_booking(
            driver_profile=self.driver_profile,
            payment=payment,
            amount_paid=payment.amount,
            grand_total=payment.amount,
            payment_status='paid',
            status='confirmed',
            pickup_date=self.base_pickup_date,
            pickup_time=self.base_pickup_time,
            payment_method='online_full',
        )

        # Cancel 2 days before pickup (minimal refund threshold is 1 day, partial is 3 days)
        cancellation_datetime = self.base_pickup_datetime - datetime.timedelta(days=2, hours=1)
        results = calculate_hire_refund_amount(hire_booking, hire_booking.payment.refund_policy_snapshot, cancellation_datetime)

        expected_refund = (Decimal('500.00') * Decimal('0.00')) / Decimal('100.00') # 0% minimal refund
        self.assertEqual(results['entitled_amount'], expected_refund)
        self.assertIn("Upfront Payment Policy: Minimal Refund Policy (0.00%)", results['details'])
        self.assertEqual(results['days_before_pickup'], 2)

    def test_upfront_no_refund_too_close(self):
        """
        Test no refund for upfront payment when cancelled too close to pickup.
        """
        payment = create_payment(
            amount=Decimal('500.00'),
            status='paid',
            driver_profile=self.driver_profile,
            refund_policy_snapshot=self.refund_policy_snapshot # Pass the snapshot
        )
        hire_booking = create_hire_booking(
            driver_profile=self.driver_profile,
            payment=payment,
            amount_paid=payment.amount,
            grand_total=payment.amount,
            payment_status='paid',
            status='confirmed',
            pickup_date=self.base_pickup_date,
            pickup_time=self.base_pickup_time,
            payment_method='online_full',
        )

        # Cancel 0 days before pickup (minimal refund threshold is 1 day)
        cancellation_datetime = self.base_pickup_datetime - datetime.timedelta(hours=12)
        results = calculate_hire_refund_amount(hire_booking, hire_booking.payment.refund_policy_snapshot, cancellation_datetime)

        self.assertEqual(results['entitled_amount'], Decimal('0.00'))
        self.assertIn("Upfront Payment Policy: No Refund Policy (Too close to pickup or after pickup)", results['details'])
        self.assertEqual(results['days_before_pickup'], 0)

    def test_upfront_no_refund_after_pickup(self):
        """
        Test no refund for upfront payment when cancelled after pickup time.
        """
        payment = create_payment(
            amount=Decimal('500.00'),
            status='paid',
            driver_profile=self.driver_profile,
            refund_policy_snapshot=self.refund_policy_snapshot # Pass the snapshot
        )
        hire_booking = create_hire_booking(
            driver_profile=self.driver_profile,
            payment=payment,
            amount_paid=payment.amount,
            grand_total=payment.amount,
            payment_status='paid',
            status='confirmed',
            pickup_date=self.base_pickup_date,
            pickup_time=self.base_pickup_time,
            payment_method='online_full',
        )

        # Cancel 1 hour after pickup
        cancellation_datetime = self.base_pickup_datetime + datetime.timedelta(hours=1)
        results = calculate_hire_refund_amount(hire_booking, hire_booking.payment.refund_policy_snapshot, cancellation_datetime)

        self.assertEqual(results['entitled_amount'], Decimal('0.00'))
        self.assertIn("Upfront Payment Policy: No Refund Policy (Too close to pickup or after pickup)", results['details'])
        self.assertEqual(results['days_before_pickup'], -1) # Negative days as cancellation is after pickup

    # --- Test Cases for Deposit Payments ---

    def test_deposit_full_refund(self):
        """
        Test full refund for deposit payment when cancelled well in advance.
        """
        # Create a deposit paid booking
        deposit_amount = Decimal('100.00') # Test with 100.00 deposit
        grand_total = Decimal('500.00')

        # Create a temporary snapshot for this test to match the deposit amount
        temp_refund_policy_snapshot = self.refund_policy_snapshot.copy()
        temp_refund_policy_snapshot['deposit_amount'] = str(deposit_amount) # Update deposit_amount in snapshot

        payment = create_payment(
            amount=deposit_amount,
            status='succeeded',
            driver_profile=self.driver_profile,
            stripe_payment_intent_id='pi_deposit_full_refund',
            refund_policy_snapshot=temp_refund_policy_snapshot # Pass the updated snapshot
        )
        hire_booking = create_hire_booking(
            driver_profile=self.driver_profile,
            payment=payment,
            amount_paid=deposit_amount,
            deposit_amount=deposit_amount,
            grand_total=grand_total, # Grand total is higher than deposit
            payment_status='deposit_paid',
            status='pending',
            pickup_date=self.base_pickup_date,
            pickup_time=self.base_pickup_time,
            payment_method='online_deposit',
        )

        # Cancel 15 days before pickup (full refund threshold for deposit is 14 days)
        cancellation_datetime = self.base_pickup_datetime - datetime.timedelta(days=15, hours=1)
        results = calculate_hire_refund_amount(hire_booking, hire_booking.payment.refund_policy_snapshot, cancellation_datetime)

        self.assertEqual(results['entitled_amount'], deposit_amount)
        self.assertIn("Deposit Payment Policy: Full Refund Policy", results['details'])
        self.assertEqual(results['days_before_pickup'], 15)

    def test_deposit_partial_refund(self):
        """
        Test partial refund for deposit payment when cancelled within the partial window.
        """
        deposit_amount = Decimal('100.00')
        grand_total = Decimal('500.00')

        temp_refund_policy_snapshot = self.refund_policy_snapshot.copy()
        temp_refund_policy_snapshot['deposit_amount'] = str(deposit_amount)

        payment = create_payment(
            amount=deposit_amount,
            status='succeeded',
            driver_profile=self.driver_profile,
            refund_policy_snapshot=temp_refund_policy_snapshot
        )
        hire_booking = create_hire_booking(
            driver_profile=self.driver_profile,
            payment=payment,
            amount_paid=deposit_amount,
            deposit_amount=deposit_amount,
            grand_total=grand_total,
            payment_status='deposit_paid',
            status='pending',
            pickup_date=self.base_pickup_date,
            pickup_time=self.base_pickup_time,
            payment_method='online_deposit',
        )

        # Cancel 10 days before pickup (partial threshold is 7 days, full is 14 days)
        cancellation_datetime = self.base_pickup_datetime - datetime.timedelta(days=10, hours=1)
        results = calculate_hire_refund_amount(hire_booking, hire_booking.payment.refund_policy_snapshot, cancellation_datetime)

        expected_refund = (deposit_amount * Decimal('75.00')) / Decimal('100.00')
        self.assertEqual(results['entitled_amount'], expected_refund)
        self.assertIn("Deposit Payment Policy: Partial Refund Policy (75.00%)", results['details'])
        self.assertEqual(results['days_before_pickup'], 10)

    def test_deposit_minimal_refund(self):
        """
        Test minimal refund for deposit payment when cancelled within the minimal window.
        """
        deposit_amount = Decimal('100.00')
        grand_total = Decimal('500.00')

        temp_refund_policy_snapshot = self.refund_policy_snapshot.copy()
        temp_refund_policy_snapshot['deposit_amount'] = str(deposit_amount)

        payment = create_payment(
            amount=deposit_amount,
            status='succeeded',
            driver_profile=self.driver_profile,
            refund_policy_snapshot=temp_refund_policy_snapshot
        )
        hire_booking = create_hire_booking(
            driver_profile=self.driver_profile,
            payment=payment,
            amount_paid=deposit_amount,
            deposit_amount=deposit_amount,
            grand_total=grand_total,
            payment_status='deposit_paid',
            status='pending',
            pickup_date=self.base_pickup_date,
            pickup_time=self.base_pickup_time,
            payment_method='online_deposit',
        )

        # Cancel 5 days before pickup (minimal threshold is 3 days, partial is 7 days)
        cancellation_datetime = self.base_pickup_datetime - datetime.timedelta(days=5, hours=1)
        results = calculate_hire_refund_amount(hire_booking, hire_booking.payment.refund_policy_snapshot, cancellation_datetime)

        expected_refund = (deposit_amount * Decimal('25.00')) / Decimal('100.00')
        self.assertEqual(results['entitled_amount'], expected_refund)
        self.assertIn("Deposit Payment Policy: Minimal Refund Policy (25.00%)", results['details'])
        self.assertEqual(results['days_before_pickup'], 5)

    def test_deposit_no_refund_too_close(self):
        """
        Test no refund for deposit payment when cancelled too close to pickup.
        """
        deposit_amount = Decimal('100.00')
        grand_total = Decimal('500.00')

        temp_refund_policy_snapshot = self.refund_policy_snapshot.copy()
        temp_refund_policy_snapshot['deposit_amount'] = str(deposit_amount)

        payment = create_payment(
            amount=deposit_amount,
            status='succeeded',
            driver_profile=self.driver_profile,
            refund_policy_snapshot=temp_refund_policy_snapshot
        )
        hire_booking = create_hire_booking(
            driver_profile=self.driver_profile,
            payment=payment,
            amount_paid=deposit_amount,
            deposit_amount=deposit_amount,
            grand_total=grand_total,
            payment_status='deposit_paid',
            status='pending',
            pickup_date=self.base_pickup_date,
            pickup_time=self.base_pickup_time,
            payment_method='online_deposit',
        )

        # Cancel 2 days before pickup (minimal threshold is 3 days)
        cancellation_datetime = self.base_pickup_datetime - datetime.timedelta(days=2, hours=1)
        results = calculate_hire_refund_amount(hire_booking, hire_booking.payment.refund_policy_snapshot, cancellation_datetime)

        self.assertEqual(results['entitled_amount'], Decimal('0.00'))
        self.assertIn("Deposit Payment Policy: No Refund Policy (Too close to pickup or after pickup)", results['details'])
        self.assertEqual(results['days_before_pickup'], 2)

    # --- Edge Cases and Other Payment Methods ---

    def test_in_store_payment_no_refund(self):
        """
        Test that in-store payments result in no calculated refund due to payment method not matching policy types.
        """
        payment = create_payment(
            amount=Decimal('500.00'),
            status='paid',
            driver_profile=self.driver_profile,
            refund_policy_snapshot=self.refund_policy_snapshot # Pass the snapshot
        )
        hire_booking = create_hire_booking(
            driver_profile=self.driver_profile,
            payment=payment,
            amount_paid=payment.amount,
            grand_total=payment.amount,
            payment_status='paid',
            status='confirmed',
            pickup_date=self.base_pickup_date,
            pickup_time=self.base_pickup_time,
            payment_method='in_store_full', # In-store payment
        )

        # Cancel well in advance, should still be no refund
        cancellation_datetime = self.base_pickup_datetime - datetime.timedelta(days=10)
        results = calculate_hire_refund_amount(hire_booking, hire_booking.payment.refund_policy_snapshot, cancellation_datetime)

        self.assertEqual(results['entitled_amount'], Decimal('0.00'))
        # Updated expected message to match the logic in hire_refund_calc.py
        self.assertIn("No Refund Policy: Refund for 'Full Payment Store' payment method is handled manually.", results['details'])
        self.assertEqual(results['days_before_pickup'], 'N/A') # Days before pickup is N/A for manual refunds

    def test_unrecognized_payment_method_no_refund(self):
        """
        Test that unrecognized or None payment methods result in no calculated refund.
        """
        # First booking scenario
        payment_1 = create_payment(
            amount=Decimal('500.00'),
            status='paid',
            driver_profile=self.driver_profile,
            stripe_payment_intent_id='pi_unrec_1',
            refund_policy_snapshot=self.refund_policy_snapshot # Pass the snapshot
        )
        hire_booking_1 = create_hire_booking(
            driver_profile=self.driver_profile,
            payment=payment_1,
            amount_paid=payment_1.amount,
            grand_total=payment_1.amount,
            payment_status='paid',
            status='confirmed',
            pickup_date=self.base_pickup_date,
            pickup_time=self.base_pickup_time,
            payment_method='some_new_method', # Unrecognized method
        )

        cancellation_datetime = self.base_pickup_datetime - datetime.timedelta(days=10)
        results = calculate_hire_refund_amount(hire_booking_1, hire_booking_1.payment.refund_policy_snapshot, cancellation_datetime)

        self.assertEqual(results['entitled_amount'], Decimal('0.00'))
        # Updated expected message to match the logic in hire_refund_calc.py
        self.assertIn("No Refund Policy: Refund for 'some_new_method' payment method is handled manually.", results['details'])
        self.assertEqual(results['days_before_pickup'], 'N/A') # Days before pickup is N/A for manual refunds

        # Test with payment_method=None - create a NEW payment for this booking
        payment_2 = create_payment(
            amount=Decimal('500.00'),
            status='paid',
            driver_profile=self.driver_profile,
            stripe_payment_intent_id='pi_unrec_2',
            refund_policy_snapshot=self.refund_policy_snapshot # Pass the snapshot
        )
        hire_booking_none_method = create_hire_booking(
            driver_profile=self.driver_profile,
            payment=payment_2, # Use a new payment object
            amount_paid=payment_2.amount,
            grand_total=payment_2.amount,
            payment_status='paid',
            status='confirmed',
            pickup_date=self.base_pickup_date,
            pickup_time=self.base_pickup_time,
            payment_method=None,
        )

        results_none = calculate_hire_refund_amount(hire_booking_none_method, hire_booking_none_method.payment.refund_policy_snapshot, cancellation_datetime)
        self.assertEqual(results_none['entitled_amount'], Decimal('0.00'))
        # Updated expected message to match the logic in hire_refund_calc.py
        self.assertIn("No Refund Policy: Refund for 'None' payment method is handled manually.", results_none['details'])
        self.assertEqual(results_none['days_before_pickup'], 'N/A') # Days before pickup is N/A for manual refunds


    def test_cancellation_exactly_at_thresholds(self):
        """
        Test cancellation exactly at the boundary of refund thresholds.
        """
        payment = create_payment(
            amount=Decimal('500.00'),
            status='paid',
            driver_profile=self.driver_profile,
            refund_policy_snapshot=self.refund_policy_snapshot # Pass the snapshot
        )
        hire_booking = create_hire_booking(
            driver_profile=self.driver_profile,
            payment=payment,
            amount_paid=payment.amount,
            grand_total=payment.amount,
            payment_status='paid',
            status='confirmed',
            pickup_date=self.base_pickup_date,
            pickup_time=self.base_pickup_time,
            payment_method='online_full',
        )

        # Exactly 7 days before (full refund)
        cancellation_datetime_full = self.base_pickup_datetime - datetime.timedelta(days=7)
        results_full = calculate_hire_refund_amount(hire_booking, hire_booking.payment.refund_policy_snapshot, cancellation_datetime_full)
        self.assertEqual(results_full['entitled_amount'], Decimal('500.00'))
        self.assertIn("Upfront Payment Policy: Full Refund Policy", results_full['details'])
        self.assertEqual(results_full['days_before_pickup'], 7)

        # Exactly 3 days before (partial refund)
        cancellation_datetime_partial = self.base_pickup_datetime - datetime.timedelta(days=3)
        results_partial = calculate_hire_refund_amount(hire_booking, hire_booking.payment.refund_policy_snapshot, cancellation_datetime_partial)
        expected_partial = (Decimal('500.00') * Decimal('50.00')) / Decimal('100.00')
        self.assertEqual(results_partial['entitled_amount'], expected_partial)
        # Expected string now includes "50.00%" due to str() conversion in snapshot
        self.assertIn("Upfront Payment Policy: Partial Refund Policy (50.00%)", results_partial['details'])
        self.assertEqual(results_partial['days_before_pickup'], 3)

        # Exactly 1 day before (minimal refund)
        cancellation_datetime_minimal = self.base_pickup_datetime - datetime.timedelta(days=1)
        results_minimal = calculate_hire_refund_amount(hire_booking, hire_booking.payment.refund_policy_snapshot, cancellation_datetime_minimal)
        expected_minimal = (Decimal('500.00') * Decimal('0.00')) / Decimal('100.00')
        self.assertEqual(results_minimal['entitled_amount'], expected_minimal)
        self.assertIn("Upfront Payment Policy: Minimal Refund Policy (0.00%)", results_minimal['details'])
        self.assertEqual(results_minimal['days_before_pickup'], 1)

        # Just under 1 day before (no refund)
        cancellation_datetime_no_refund = self.base_pickup_datetime - datetime.timedelta(hours=23)
        results_no_refund = calculate_hire_refund_amount(hire_booking, hire_booking.payment.refund_policy_snapshot, cancellation_datetime_no_refund)
        self.assertEqual(results_no_refund['entitled_amount'], Decimal('0.00'))
        self.assertIn("Upfront Payment Policy: No Refund Policy (Too close to pickup or after pickup)", results_no_refund['details'])
        self.assertEqual(results_no_refund['days_before_pickup'], 0)


    def test_hire_settings_not_found_fallback(self):
        """
        Test that the function returns 'No refund policy snapshot available' if payment has no snapshot.
        """
        # Delete the HireSettings created in setUp to ensure no fallback from global settings
        HireSettings.objects.all().delete()

        # Create a payment with an empty refund_policy_snapshot
        payment = create_payment(
            amount=Decimal('500.00'),
            status='paid',
            driver_profile=self.driver_profile,
            refund_policy_snapshot={} # Empty snapshot
        )
        hire_booking = create_hire_booking(
            driver_profile=self.driver_profile,
            payment=payment,
            amount_paid=payment.amount,
            grand_total=payment.amount,
            payment_status='paid',
            status='confirmed',
            pickup_date=self.base_pickup_date,
            pickup_time=self.base_pickup_time,
            payment_method='online_full',
        )

        cancellation_datetime = self.base_pickup_datetime - datetime.timedelta(days=8)
        results_full = calculate_hire_refund_amount(hire_booking, hire_booking.payment.refund_policy_snapshot, cancellation_datetime)

        self.assertEqual(results_full['entitled_amount'], Decimal('0.00'))
        self.assertEqual(results_full['details'], "No refund policy snapshot available for this booking.")
        self.assertEqual(results_full['policy_applied'], "N/A")


    def test_refund_amount_never_exceeds_paid_amount(self):
        """
        Ensure the calculated refund amount never exceeds the total paid for calculation.
        This is a safeguard against misconfigurations or floating point errors.
        """
        payment = create_payment(
            amount=Decimal('100.00'),
            status='paid',
            driver_profile=self.driver_profile,
            refund_policy_snapshot=self.refund_policy_snapshot # Pass the snapshot
        )
        hire_booking = create_hire_booking(
            driver_profile=self.driver_profile,
            payment=payment,
            amount_paid=payment.amount,
            grand_total=payment.amount,
            payment_status='paid',
            status='confirmed',
            pickup_date=self.base_pickup_date,
            pickup_time=self.base_pickup_time,
            payment_method='online_full',
        )

        # Set a scenario where calculation *might* exceed (e.g., if percentage was 101%)
        # Temporarily modify the snapshot for this test
        temp_snapshot = self.refund_policy_snapshot.copy()
        temp_snapshot['cancellation_upfront_full_refund_days'] = 0 # Make it always full refund

        # If total_paid_for_calculation is 100, and logic somehow yields 100.01, it should be capped at 100.00
        # Forcing a scenario where refund_amount could theoretically be slightly higher due to floating point
        # (though with Decimal it's less likely, it's good to have the safeguard)
        calculated_value_that_might_exceed = Decimal('100.0000000000000000000000000001') # Simulate a slight overshoot
        
        # Manually override the calculation in the test to check the capping logic
        original_calculate_hire_refund_amount = calculate_hire_refund_amount

        def mock_calculate_hire_refund_amount_with_overshoot(booking, refund_policy_snapshot, cancellation_datetime):
            results = original_calculate_hire_refund_amount(booking, refund_policy_snapshot, cancellation_datetime)
            # Introduce an artificial overshoot for testing the max() function
            if "Full Refund Policy" in results['details']:
                results['entitled_amount'] = calculated_value_that_might_exceed
            return results

        # Temporarily replace the function in the module's global scope
        import sys
        sys.modules['payments.hire_refund_calc'].calculate_hire_refund_amount = mock_calculate_hire_refund_amount_with_overshoot

        cancellation_datetime = self.base_pickup_datetime - datetime.timedelta(days=10)
        results = calculate_hire_refund_amount(hire_booking, temp_snapshot, cancellation_datetime) # Use temp_snapshot here

        # Restore original function
        sys.modules['payments.hire_refund_calc'].calculate_hire_refund_amount = original_calculate_hire_refund_amount

        self.assertEqual(results['entitled_amount'], Decimal('100.00')) # Should be capped at the original amount
        self.assertLessEqual(results['entitled_amount'], hire_booking.amount_paid)


    def test_refund_amount_never_negative(self):
        """
        Ensure the calculated refund amount is never negative.
        """
        payment = create_payment(
            amount=Decimal('500.00'),
            status='paid',
            driver_profile=self.driver_profile,
            refund_policy_snapshot=self.refund_policy_snapshot # Pass the snapshot
        )
        hire_booking = create_hire_booking(
            driver_profile=self.driver_profile,
            payment=payment,
            amount_paid=payment.amount,
            grand_total=payment.amount,
            payment_status='paid',
            status='confirmed',
            pickup_date=self.base_pickup_date,
            pickup_time=self.base_pickup_time,
            payment_method='online_full',
        )

        # Cancel after pickup, should result in 0.00, not negative
        cancellation_datetime = self.base_pickup_datetime + datetime.timedelta(days=5)
        results = calculate_hire_refund_amount(hire_booking, hire_booking.payment.refund_policy_snapshot, cancellation_datetime)

        self.assertEqual(results['entitled_amount'], Decimal('0.00'))
        self.assertGreaterEqual(results['entitled_amount'], Decimal('0.00'))

    def test_details_include_all_relevant_info(self):
        """
        Test that the details dictionary contains all expected information.
        """
        payment = create_payment(
            amount=Decimal('500.00'),
            status='paid',
            driver_profile=self.driver_profile,
            refund_policy_snapshot=self.refund_policy_snapshot # Pass the snapshot
        )
        hire_booking = create_hire_booking(
            driver_profile=self.driver_profile,
            payment=payment,
            amount_paid=payment.amount,
            grand_total=payment.amount,
            payment_status='paid',
            status='confirmed',
            pickup_date=self.base_pickup_date,
            pickup_time=self.base_pickup_time,
            payment_method='online_full',
        )

        cancellation_datetime = self.base_pickup_datetime - datetime.timedelta(days=5)
        results = calculate_hire_refund_amount(hire_booking, hire_booking.payment.refund_policy_snapshot, cancellation_datetime)

        # Assert that the main keys are present in the returned dictionary
        self.assertIn('entitled_amount', results)
        self.assertIn('details', results)
        self.assertIn('policy_applied', results)
        self.assertIn('days_before_pickup', results)

        # Assert that the 'details' string contains the expected information
        self.assertIn("Cancellation 5 days before pickup.", results['details'])
        self.assertIn("Policy: Upfront Payment Policy: Partial Refund Policy (50.00%).", results['details'])
        self.assertIn("Calculated: 250.00 (50.00% of 500.00).", results['details'])

        # Assert specific values
        self.assertEqual(results['entitled_amount'], Decimal('250.00'))
        self.assertEqual(results['days_before_pickup'], 5)
        self.assertEqual(results['policy_applied'], "Upfront Payment Policy: Partial Refund Policy (50.00%)")

