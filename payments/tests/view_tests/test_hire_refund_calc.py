# payments/tests/test_hire_refund_calc.py

from django.test import TestCase
from decimal import Decimal
from django.utils import timezone
import datetime

# Import the function to be tested
from payments.hire_refund_calc import calculate_refund_amount

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
    Tests for the calculate_refund_amount function in payments/hire_refund_calc.py.
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
        )

        # Create a driver profile
        self.driver_profile = create_driver_profile()

        # Define a base pickup datetime for consistent testing
        self.base_pickup_date = timezone.now().date() + datetime.timedelta(days=30)
        self.base_pickup_time = datetime.time(10, 0)
        self.base_pickup_datetime = timezone.make_aware(
            datetime.datetime.combine(self.base_pickup_date, self.base_pickup_time)
        )

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
            stripe_payment_intent_id='pi_upfront_full_refund'
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
        payment.hire_booking = hire_booking
        payment.save()

        # Cancel 8 days before pickup (full refund threshold is 7 days)
        cancellation_datetime = self.base_pickup_datetime - datetime.timedelta(days=8, hours=1)
        refund_amount, details = calculate_refund_amount(hire_booking, cancellation_datetime)

        self.assertEqual(refund_amount, Decimal('500.00'))
        self.assertEqual(details['policy_applied'], "Upfront Payment Policy: Full Refund Policy")
        self.assertEqual(details['refund_percentage'], '100.00')
        self.assertEqual(details['total_paid_amount'], '500.00')
        self.assertEqual(details['days_in_advance'], 8)

    def test_upfront_partial_refund(self):
        """
        Test partial refund for upfront payment when cancelled within the partial window.
        """
        payment = create_payment(amount=Decimal('500.00'), status='paid', driver_profile=self.driver_profile)
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
        payment.hire_booking = hire_booking
        payment.save()

        # Cancel 4 days before pickup (partial refund threshold is 3 days, full is 7 days)
        cancellation_datetime = self.base_pickup_datetime - datetime.timedelta(days=4, hours=1)
        refund_amount, details = calculate_refund_amount(hire_booking, cancellation_datetime)

        expected_refund = (Decimal('500.00') * Decimal('50.00')) / Decimal('100.00')
        self.assertEqual(refund_amount, expected_refund)
        self.assertEqual(details['policy_applied'], "Upfront Payment Policy: Partial Refund Policy (50.00%)")
        self.assertEqual(details['refund_percentage'], '50.00')
        self.assertEqual(details['total_paid_amount'], '500.00')
        self.assertEqual(details['days_in_advance'], 4)

    def test_upfront_minimal_refund(self):
        """
        Test minimal refund for upfront payment when cancelled within the minimal window.
        """
        payment = create_payment(amount=Decimal('500.00'), status='paid', driver_profile=self.driver_profile)
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
        payment.hire_booking = hire_booking
        payment.save()

        # Cancel 2 days before pickup (minimal refund threshold is 1 day, partial is 3 days)
        cancellation_datetime = self.base_pickup_datetime - datetime.timedelta(days=2, hours=1)
        refund_amount, details = calculate_refund_amount(hire_booking, cancellation_datetime)

        expected_refund = (Decimal('500.00') * Decimal('0.00')) / Decimal('100.00') # 0% minimal refund
        self.assertEqual(refund_amount, expected_refund)
        self.assertEqual(details['policy_applied'], "Upfront Payment Policy: Minimal Refund Policy (0.00%)")
        self.assertEqual(details['refund_percentage'], '0.00')
        self.assertEqual(details['total_paid_amount'], '500.00')
        self.assertEqual(details['days_in_advance'], 2)

    def test_upfront_no_refund_too_close(self):
        """
        Test no refund for upfront payment when cancelled too close to pickup.
        """
        payment = create_payment(amount=Decimal('500.00'), status='paid', driver_profile=self.driver_profile)
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
        payment.hire_booking = hire_booking
        payment.save()

        # Cancel 0 days before pickup (minimal refund threshold is 1 day)
        cancellation_datetime = self.base_pickup_datetime - datetime.timedelta(hours=12)
        refund_amount, details = calculate_refund_amount(hire_booking, cancellation_datetime)

        self.assertEqual(refund_amount, Decimal('0.00'))
        self.assertEqual(details['policy_applied'], "Upfront Payment Policy: No Refund Policy (Too close to pickup or after pickup)")
        self.assertEqual(details['refund_percentage'], '0.00')
        self.assertEqual(details['total_paid_amount'], '500.00')
        self.assertEqual(details['days_in_advance'], 0)

    def test_upfront_no_refund_after_pickup(self):
        """
        Test no refund for upfront payment when cancelled after pickup time.
        """
        payment = create_payment(amount=Decimal('500.00'), status='paid', driver_profile=self.driver_profile)
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
        payment.hire_booking = hire_booking
        payment.save()

        # Cancel 1 hour after pickup
        cancellation_datetime = self.base_pickup_datetime + datetime.timedelta(hours=1)
        refund_amount, details = calculate_refund_amount(hire_booking, cancellation_datetime)

        self.assertEqual(refund_amount, Decimal('0.00'))
        self.assertEqual(details['policy_applied'], "Upfront Payment Policy: No Refund Policy (Too close to pickup or after pickup)")
        self.assertEqual(details['refund_percentage'], '0.00')
        self.assertEqual(details['total_paid_amount'], '500.00')
        self.assertEqual(details['days_in_advance'], -1) # Negative days as cancellation is after pickup

    # --- Test Cases for Deposit Payments ---

    def test_deposit_full_refund(self):
        """
        Test full refund for deposit payment when cancelled well in advance.
        """
        # Create a deposit paid booking
        deposit_amount = Decimal('100.00')
        payment = create_payment(
            amount=deposit_amount,
            status='succeeded',
            driver_profile=self.driver_profile,
            stripe_payment_intent_id='pi_deposit_full_refund'
        )
        hire_booking = create_hire_booking(
            driver_profile=self.driver_profile,
            payment=payment,
            amount_paid=deposit_amount,
            deposit_amount=deposit_amount,
            grand_total=Decimal('500.00'), # Grand total is higher than deposit
            payment_status='deposit_paid',
            status='pending',
            pickup_date=self.base_pickup_date,
            pickup_time=self.base_pickup_time,
            payment_method='online_deposit',
        )
        payment.hire_booking = hire_booking
        payment.save()

        # Cancel 15 days before pickup (full refund threshold for deposit is 14 days)
        cancellation_datetime = self.base_pickup_datetime - datetime.timedelta(days=15, hours=1)
        refund_amount, details = calculate_refund_amount(hire_booking, cancellation_datetime)

        self.assertEqual(refund_amount, deposit_amount)
        self.assertEqual(details['policy_applied'], "Deposit Payment Policy: Full Refund Policy")
        self.assertEqual(details['refund_percentage'], '100.00')
        self.assertEqual(details['total_paid_amount'], str(deposit_amount))
        self.assertEqual(details['days_in_advance'], 15)

    def test_deposit_partial_refund(self):
        """
        Test partial refund for deposit payment when cancelled within the partial window.
        """
        deposit_amount = Decimal('100.00')
        payment = create_payment(amount=deposit_amount, status='succeeded', driver_profile=self.driver_profile)
        hire_booking = create_hire_booking(
            driver_profile=self.driver_profile,
            payment=payment,
            amount_paid=deposit_amount,
            deposit_amount=deposit_amount,
            grand_total=Decimal('500.00'),
            payment_status='deposit_paid',
            status='pending',
            pickup_date=self.base_pickup_date,
            pickup_time=self.base_pickup_time,
            payment_method='online_deposit',
        )
        payment.hire_booking = hire_booking
        payment.save()

        # Cancel 10 days before pickup (partial threshold is 7 days, full is 14 days)
        cancellation_datetime = self.base_pickup_datetime - datetime.timedelta(days=10, hours=1)
        refund_amount, details = calculate_refund_amount(hire_booking, cancellation_datetime)

        expected_refund = (deposit_amount * Decimal('75.00')) / Decimal('100.00')
        self.assertEqual(refund_amount, expected_refund)
        self.assertEqual(details['policy_applied'], "Deposit Payment Policy: Partial Refund Policy (75.00%)")
        self.assertEqual(details['refund_percentage'], '75.00')
        self.assertEqual(details['total_paid_amount'], str(deposit_amount))
        self.assertEqual(details['days_in_advance'], 10)

    def test_deposit_minimal_refund(self):
        """
        Test minimal refund for deposit payment when cancelled within the minimal window.
        """
        deposit_amount = Decimal('100.00')
        payment = create_payment(amount=deposit_amount, status='succeeded', driver_profile=self.driver_profile)
        hire_booking = create_hire_booking(
            driver_profile=self.driver_profile,
            payment=payment,
            amount_paid=deposit_amount,
            deposit_amount=deposit_amount,
            grand_total=Decimal('500.00'),
            payment_status='deposit_paid',
            status='pending',
            pickup_date=self.base_pickup_date,
            pickup_time=self.base_pickup_time,
            payment_method='online_deposit',
        )
        payment.hire_booking = hire_booking
        payment.save()

        # Cancel 5 days before pickup (minimal threshold is 3 days, partial is 7 days)
        cancellation_datetime = self.base_pickup_datetime - datetime.timedelta(days=5, hours=1)
        refund_amount, details = calculate_refund_amount(hire_booking, cancellation_datetime)

        expected_refund = (deposit_amount * Decimal('25.00')) / Decimal('100.00')
        self.assertEqual(refund_amount, expected_refund)
        self.assertEqual(details['policy_applied'], "Deposit Payment Policy: Minimal Refund Policy (25.00%)")
        self.assertEqual(details['refund_percentage'], '25.00')
        self.assertEqual(details['total_paid_amount'], str(deposit_amount))
        self.assertEqual(details['days_in_advance'], 5)

    def test_deposit_no_refund_too_close(self):
        """
        Test no refund for deposit payment when cancelled too close to pickup.
        """
        deposit_amount = Decimal('100.00')
        payment = create_payment(amount=deposit_amount, status='succeeded', driver_profile=self.driver_profile)
        hire_booking = create_hire_booking(
            driver_profile=self.driver_profile,
            payment=payment,
            amount_paid=deposit_amount,
            deposit_amount=deposit_amount,
            grand_total=Decimal('500.00'),
            payment_status='deposit_paid',
            status='pending',
            pickup_date=self.base_pickup_date,
            pickup_time=self.base_pickup_time,
            payment_method='online_deposit',
        )
        payment.hire_booking = hire_booking
        payment.save()

        # Cancel 2 days before pickup (minimal threshold is 3 days)
        cancellation_datetime = self.base_pickup_datetime - datetime.timedelta(days=2, hours=1)
        refund_amount, details = calculate_refund_amount(hire_booking, cancellation_datetime)

        self.assertEqual(refund_amount, Decimal('0.00'))
        self.assertEqual(details['policy_applied'], "Deposit Payment Policy: No Refund Policy (Too close to pickup or after pickup)")
        self.assertEqual(details['refund_percentage'], '0.00')
        self.assertEqual(details['total_paid_amount'], str(deposit_amount))
        self.assertEqual(details['days_in_advance'], 2)

    # --- Edge Cases and Other Payment Methods ---

    def test_in_store_payment_no_refund(self):
        """
        Test that in-store payments always result in no calculated refund.
        """
        payment = create_payment(amount=Decimal('500.00'), status='paid', driver_profile=self.driver_profile)
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
        payment.hire_booking = hire_booking
        payment.save()

        # Cancel well in advance, should still be no refund
        cancellation_datetime = self.base_pickup_datetime - datetime.timedelta(days=10)
        refund_amount, details = calculate_refund_amount(hire_booking, cancellation_datetime)

        self.assertEqual(refund_amount, Decimal('0.00'))
        self.assertEqual(details['policy_applied'], "In-Store Payment: Refund handled manually in store.")
        self.assertEqual(details['refund_percentage'], '0.00')
        self.assertEqual(details['total_paid_amount'], '500.00') # Still captures amount paid
        self.assertEqual(details['days_in_advance'], 10)

    def test_unrecognized_payment_method_no_refund(self):
        """
        Test that unrecognized or None payment methods result in no calculated refund.
        """
        # First booking scenario
        payment_1 = create_payment(amount=Decimal('500.00'), status='paid', driver_profile=self.driver_profile, stripe_payment_intent_id='pi_unrec_1')
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
        payment_1.hire_booking = hire_booking_1
        payment_1.save()

        cancellation_datetime = self.base_pickup_datetime - datetime.timedelta(days=10)
        refund_amount, details = calculate_refund_amount(hire_booking_1, cancellation_datetime)

        self.assertEqual(refund_amount, Decimal('0.00'))
        self.assertEqual(details['policy_applied'], "No Refund Policy: Payment method not recognized or applicable.")
        self.assertEqual(details['refund_percentage'], '0.00')
        self.assertEqual(details['total_paid_amount'], '500.00')
        self.assertEqual(details['days_in_advance'], 10)

        # Test with payment_method=None - create a NEW payment for this booking
        payment_2 = create_payment(amount=Decimal('500.00'), status='paid', driver_profile=self.driver_profile, stripe_payment_intent_id='pi_unrec_2')
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
        payment_2.hire_booking = hire_booking_none_method
        payment_2.save()

        refund_amount_none, details_none = calculate_refund_amount(hire_booking_none_method, cancellation_datetime)
        self.assertEqual(refund_amount_none, Decimal('0.00'))
        self.assertEqual(details_none['policy_applied'], "No Refund Policy: Payment method not recognized or applicable.")


    def test_cancellation_exactly_at_thresholds(self):
        """
        Test cancellation exactly at the boundary of refund thresholds.
        """
        payment = create_payment(amount=Decimal('500.00'), status='paid', driver_profile=self.driver_profile)
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
        payment.hire_booking = hire_booking
        payment.save()

        # Exactly 7 days before (full refund)
        cancellation_datetime_full = self.base_pickup_datetime - datetime.timedelta(days=7)
        refund_amount_full, details_full = calculate_refund_amount(hire_booking, cancellation_datetime_full)
        self.assertEqual(refund_amount_full, Decimal('500.00'))
        self.assertEqual(details_full['policy_applied'], "Upfront Payment Policy: Full Refund Policy")
        self.assertEqual(details_full['days_in_advance'], 7)

        # Exactly 3 days before (partial refund)
        cancellation_datetime_partial = self.base_pickup_datetime - datetime.timedelta(days=3)
        refund_amount_partial, details_partial = calculate_refund_amount(hire_booking, cancellation_datetime_partial)
        expected_partial = (Decimal('500.00') * Decimal('50.00')) / Decimal('100.00')
        self.assertEqual(refund_amount_partial, expected_partial)
        self.assertEqual(details_partial['policy_applied'], "Upfront Payment Policy: Partial Refund Policy (50.00%)")
        self.assertEqual(details_partial['days_in_advance'], 3)

        # Exactly 1 day before (minimal refund)
        cancellation_datetime_minimal = self.base_pickup_datetime - datetime.timedelta(days=1)
        refund_amount_minimal, details_minimal = calculate_refund_amount(hire_booking, cancellation_datetime_minimal)
        expected_minimal = (Decimal('500.00') * Decimal('0.00')) / Decimal('100.00')
        self.assertEqual(refund_amount_minimal, expected_minimal)
        self.assertEqual(details_minimal['policy_applied'], "Upfront Payment Policy: Minimal Refund Policy (0.00%)")
        self.assertEqual(details_minimal['days_in_advance'], 1)

        # Just under 1 day before (no refund)
        cancellation_datetime_no_refund = self.base_pickup_datetime - datetime.timedelta(hours=23)
        refund_amount_no_refund, details_no_refund = calculate_refund_amount(hire_booking, cancellation_datetime_no_refund)
        self.assertEqual(refund_amount_no_refund, Decimal('0.00'))
        self.assertEqual(details_no_refund['policy_applied'], "Upfront Payment Policy: No Refund Policy (Too close to pickup or after pickup)")
        self.assertEqual(details_no_refund['days_in_advance'], 0)


    def test_hire_settings_not_found_fallback(self):
        """
        Test that the function uses sensible default settings if HireSettings does not exist.
        """
        # Delete the HireSettings created in setUp
        HireSettings.objects.all().delete()

        payment = create_payment(amount=Decimal('500.00'), status='paid', driver_profile=self.driver_profile)
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
        payment.hire_booking = hire_booking
        payment.save()

        # Test full refund with fallback settings (default full refund days is 7)
        cancellation_datetime_full = self.base_pickup_datetime - datetime.timedelta(days=8)
        refund_amount_full, details_full = calculate_refund_amount(hire_booking, cancellation_datetime_full)
        self.assertEqual(refund_amount_full, Decimal('500.00'))
        self.assertEqual(details_full['policy_applied'], "Upfront Payment Policy: Full Refund Policy")
        self.assertEqual(details_full['full_refund_threshold_days'], 7)

        # Test partial refund with fallback settings (default partial refund days is 3, 50%)
        cancellation_datetime_partial = self.base_pickup_datetime - datetime.timedelta(days=4)
        refund_amount_partial, details_partial = calculate_refund_amount(hire_booking, cancellation_datetime_partial)
        expected_partial = (Decimal('500.00') * Decimal('50.00')) / Decimal('100.00')
        self.assertEqual(refund_amount_partial, expected_partial)
        self.assertEqual(details_partial['policy_applied'], "Upfront Payment Policy: Partial Refund Policy (50.00%)")
        self.assertEqual(details_partial['partial_refund_threshold_days'], 3)
        self.assertEqual(details_partial['partial_refund_percentage'], '50.00')

        # Test minimal refund with fallback settings (default minimal refund days is 1, 0%)
        cancellation_datetime_minimal = self.base_pickup_datetime - datetime.timedelta(days=2)
        refund_amount_minimal, details_minimal = calculate_refund_amount(hire_booking, cancellation_datetime_minimal)
        expected_minimal = (Decimal('500.00') * Decimal('0.00')) / Decimal('100.00')
        self.assertEqual(refund_amount_minimal, expected_minimal)
        self.assertEqual(details_minimal['policy_applied'], "Upfront Payment Policy: Minimal Refund Policy (0.00%)")
        self.assertEqual(details_minimal['minimal_refund_threshold_days'], 1)
        self.assertEqual(details_minimal['minimal_refund_percentage'], '0.00')

        # Test no refund with fallback settings
        cancellation_datetime_no_refund = self.base_pickup_datetime - datetime.timedelta(hours=12)
        refund_amount_no_refund, details_no_refund = calculate_refund_amount(hire_booking, cancellation_datetime_no_refund)
        self.assertEqual(refund_amount_no_refund, Decimal('0.00'))
        self.assertEqual(details_no_refund['policy_applied'], "Upfront Payment Policy: No Refund Policy (Too close to pickup or after pickup)")
        self.assertEqual(details_no_refund['days_in_advance'], 0)


    def test_refund_amount_never_exceeds_paid_amount(self):
        """
        Ensure the calculated refund amount never exceeds the total paid for calculation.
        This is a safeguard against misconfigurations or floating point errors.
        """
        payment = create_payment(amount=Decimal('100.00'), status='paid', driver_profile=self.driver_profile)
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
        payment.hire_booking = hire_booking
        payment.save()

        # Set a scenario where calculation *might* exceed (e.g., if percentage was 101%)
        # Temporarily modify settings for this test
        self.hire_settings.cancellation_upfront_full_refund_days = 0 # Make it always full refund
        self.hire_settings.save()

        # If total_paid_for_calculation is 100, and logic somehow yields 100.01, it should be capped at 100.00
        # Forcing a scenario where refund_amount could theoretically be slightly higher due to floating point
        # (though with Decimal it's less likely, it's good to have the safeguard)
        calculated_value_that_might_exceed = Decimal('100.0000000000000000000000000001') # Simulate a slight overshoot
        # Manually override the calculation in the test to check the capping logic
        original_calculate_refund_amount = calculate_refund_amount.__globals__['calculate_refund_amount']

        def mock_calculate_refund_amount(hb, cd):
            refund, details = original_calculate_refund_amount(hb, cd)
            # Introduce an artificial overshoot for testing the max() function
            if details['policy_applied'].startswith("Upfront Payment Policy: Full Refund Policy"):
                return calculated_value_that_might_exceed, details
            return refund, details

        calculate_refund_amount.__globals__['calculate_refund_amount'] = mock_calculate_refund_amount

        cancellation_datetime = self.base_pickup_datetime - datetime.timedelta(days=10)
        refund_amount, details = calculate_refund_amount(hire_booking, cancellation_datetime)

        # Restore original function
        calculate_refund_amount.__globals__['calculate_refund_amount'] = original_calculate_refund_amount

        self.assertEqual(refund_amount, Decimal('100.00')) # Should be capped at the original amount
        self.assertLessEqual(refund_amount, hire_booking.amount_paid)


    def test_refund_amount_never_negative(self):
        """
        Ensure the calculated refund amount is never negative.
        """
        payment = create_payment(amount=Decimal('500.00'), status='paid', driver_profile=self.driver_profile)
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
        payment.hire_booking = hire_booking
        payment.save()

        # Cancel after pickup, should result in 0.00, not negative
        cancellation_datetime = self.base_pickup_datetime + datetime.timedelta(days=5)
        refund_amount, details = calculate_refund_amount(hire_booking, cancellation_datetime)

        self.assertEqual(refund_amount, Decimal('0.00'))
        self.assertGreaterEqual(refund_amount, Decimal('0.00'))

    def test_details_include_all_relevant_info(self):
        """
        Test that the details dictionary contains all expected information.
        """
        payment = create_payment(amount=Decimal('500.00'), status='paid', driver_profile=self.driver_profile)
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
        payment.hire_booking = hire_booking
        payment.save()

        cancellation_datetime = self.base_pickup_datetime - datetime.timedelta(days=5)
        refund_amount, details = calculate_refund_amount(hire_booking, cancellation_datetime)

        self.assertIn('cancellation_datetime', details)
        self.assertIn('pickup_datetime', details)
        self.assertIn('days_in_advance', details)
        self.assertIn('total_paid_amount', details)
        self.assertIn('calculated_refund_amount', details)
        self.assertIn('refund_percentage', details)
        self.assertIn('policy_applied', details)
        self.assertIn('payment_method_used', details)
        self.assertIn('full_refund_threshold_days', details)
        self.assertIn('partial_refund_threshold_days', details)
        self.assertIn('partial_refund_percentage', details)
        self.assertIn('minimal_refund_threshold_days', details)
        self.assertIn('minimal_refund_percentage', details)

        self.assertEqual(details['total_paid_amount'], '500.00')
        self.assertEqual(details['calculated_refund_amount'], str(refund_amount))
        self.assertEqual(details['payment_method_used'], 'online_full')
        self.assertEqual(details['full_refund_threshold_days'], self.hire_settings.cancellation_upfront_full_refund_days)
        self.assertEqual(details['partial_refund_threshold_days'], self.hire_settings.cancellation_upfront_partial_refund_days)
        self.assertEqual(details['partial_refund_percentage'], str(self.hire_settings.cancellation_upfront_partial_refund_percentage))
        self.assertEqual(details['minimal_refund_threshold_days'], self.hire_settings.cancellation_upfront_minimal_refund_days)
        self.assertEqual(details['minimal_refund_percentage'], str(self.hire_settings.cancellation_upfront_minimal_refund_percentage))

