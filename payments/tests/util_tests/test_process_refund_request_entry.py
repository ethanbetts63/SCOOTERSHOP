import datetime
from decimal import Decimal
from unittest import mock

from django.test import TestCase
from datetime import timezone as dt_timezone # Use standard library timezone for utc

# Import the utility function to be tested
from payments.utils.process_refund_request_entry import process_refund_request_entry

# Import the model factories as per your specified path
from payments.tests.test_helpers.model_factories import (
    PaymentFactory,
    HireBookingFactory,
    ServiceBookingFactory,
    RefundRequestFactory,
)


class ProcessRefundRequestEntryTestCase(TestCase):
    """
    Tests for the process_refund_request_entry utility function.
    This function handles the creation or updating of RefundRequest instances
    based on Stripe webhook data.
    """

    def setUp(self):
        """
        Set up common data and mock for consistent timestamps.
        """
        # Mock timezone.now for consistent timestamps in created_at, requested_at, processed_at
        # Use datetime.timezone.utc for setting tzinfo directly.
        self.mock_now = datetime.datetime(2023, 1, 15, 12, 0, 0, tzinfo=dt_timezone.utc)
        self.mock_now_patch = mock.patch('django.utils.timezone.now', return_value=self.mock_now)
        self.mock_now_patch.start()

    def tearDown(self):
        """
        Clean up after tests.
        """
        self.mock_now_patch.stop()

    def test_create_new_refund_request_for_hire_booking(self):
        """
        Tests that a new RefundRequest is created when no existing one matches
        and the payment is linked to a HireBooking.
        """
        hire_booking = HireBookingFactory()
        payment = PaymentFactory(hire_booking=hire_booking, service_booking=None, status='succeeded')
        
        extracted_data = {
            'stripe_refund_id': 're_new_hire_123',
            'refunded_amount_decimal': Decimal('50.00'),
        }

        # Ensure no RefundRequest exists initially for this payment
        self.assertEqual(hire_booking.refund_requests.count(), 0)
        self.assertEqual(payment.refund_requests.count(), 0)

        refund_request = process_refund_request_entry(payment, hire_booking, 'hire_booking', extracted_data)

        # Assertions for the newly created RefundRequest
        self.assertIsNotNone(refund_request)
        self.assertEqual(refund_request.payment, payment)
        self.assertEqual(refund_request.hire_booking, hire_booking)
        self.assertIsNone(refund_request.service_booking) # Should be None for hire booking
        self.assertEqual(refund_request.stripe_refund_id, 're_new_hire_123')
        self.assertEqual(refund_request.amount_to_refund, Decimal('50.00'))
        self.assertEqual(refund_request.status, 'partially_refunded') # Payment status 'succeeded' -> 'partially_refunded'
        self.assertTrue(refund_request.is_admin_initiated)
        self.assertEqual(refund_request.processed_at, self.mock_now)
        self.assertIn("initial creation", refund_request.staff_notes)

        # Verify it was added to the database
        self.assertEqual(hire_booking.refund_requests.count(), 1)
        self.assertEqual(payment.refund_requests.count(), 1)


    def test_create_new_refund_request_for_service_booking(self):
        """
        Tests that a new RefundRequest is created when no existing one matches
        and the payment is linked to a ServiceBooking.
        """
        service_booking = ServiceBookingFactory()
        payment = PaymentFactory(hire_booking=None, service_booking=service_booking, status='succeeded')
        
        extracted_data = {
            'stripe_refund_id': 're_new_service_456',
            'refunded_amount_decimal': Decimal('75.00'),
        }

        # Ensure no RefundRequest exists initially for this payment
        self.assertEqual(service_booking.refund_requests.count(), 0)
        self.assertEqual(payment.refund_requests.count(), 0)


        refund_request = process_refund_request_entry(payment, service_booking, 'service_booking', extracted_data)

        # Assertions for the newly created RefundRequest
        self.assertIsNotNone(refund_request)
        self.assertEqual(refund_request.payment, payment)
        self.assertIsNone(refund_request.hire_booking) # Should be None for service booking
        self.assertEqual(refund_request.service_booking, service_booking)
        self.assertEqual(refund_request.stripe_refund_id, 're_new_service_456')
        self.assertEqual(refund_request.amount_to_refund, Decimal('75.00'))
        self.assertEqual(refund_request.status, 'partially_refunded')
        self.assertTrue(refund_request.is_admin_initiated)
        self.assertEqual(refund_request.processed_at, self.mock_now)
        self.assertIn("initial creation", refund_request.staff_notes)

        # Verify it was added to the database
        self.assertEqual(service_booking.refund_requests.count(), 1)
        self.assertEqual(payment.refund_requests.count(), 1)


    def test_update_existing_pending_refund_request(self):
        """
        Tests that an existing RefundRequest with a 'pending' status is updated.
        """
        hire_booking = HireBookingFactory()
        payment = PaymentFactory(hire_booking=hire_booking, status='succeeded')
        
        # Create an existing RefundRequest in 'pending' status
        existing_refund_request = RefundRequestFactory(
            payment=payment,
            hire_booking=hire_booking,
            service_booking=None,
            status='pending',
            amount_to_refund=Decimal('0.00'), # Initial amount
            stripe_refund_id=None, # No Stripe ID yet
            processed_at=None,
            staff_notes="User requested refund via frontend.",
            requested_at=self.mock_now - datetime.timedelta(days=1) # Older timestamp
        )
        initial_notes = existing_refund_request.staff_notes

        extracted_data = {
            'stripe_refund_id': 're_updated_123',
            'refunded_amount_decimal': Decimal('60.00'),
        }

        updated_refund_request = process_refund_request_entry(payment, hire_booking, 'hire_booking', extracted_data)

        # Reload the object from DB to ensure changes are persisted and reflect
        updated_refund_request.refresh_from_db()

        # Assertions for the updated RefundRequest
        self.assertEqual(updated_refund_request.id, existing_refund_request.id) # Should be the same object
        self.assertEqual(updated_refund_request.stripe_refund_id, 're_updated_123')
        self.assertEqual(updated_refund_request.amount_to_refund, Decimal('60.00'))
        self.assertEqual(updated_refund_request.status, 'partially_refunded') # Payment status 'succeeded' -> 'partially_refunded'
        self.assertEqual(updated_refund_request.processed_at, self.mock_now)
        self.assertIn("updated existing request", updated_refund_request.staff_notes)
        self.assertTrue(updated_refund_request.staff_notes.startswith(initial_notes)) # Notes should be appended


    def test_update_existing_unverified_refund_request(self):
        """
        Tests that an existing RefundRequest with an 'unverified' status is updated.
        """
        service_booking = ServiceBookingFactory()
        payment = PaymentFactory(service_booking=service_booking, status='succeeded')
        
        existing_refund_request = RefundRequestFactory(
            payment=payment,
            service_booking=service_booking,
            hire_booking=None,
            status='unverified',
            amount_to_refund=Decimal('0.00'),
            stripe_refund_id=None,
            processed_at=None,
            staff_notes="Unverified user request.",
            requested_at=self.mock_now - datetime.timedelta(hours=5)
        )
        initial_notes = existing_refund_request.staff_notes

        extracted_data = {
            'stripe_refund_id': 're_updated_unverified_789',
            'refunded_amount_decimal': Decimal('120.00'),
        }

        updated_refund_request = process_refund_request_entry(payment, service_booking, 'service_booking', extracted_data)
        updated_refund_request.refresh_from_db()

        self.assertEqual(updated_refund_request.id, existing_refund_request.id)
        self.assertEqual(updated_refund_request.stripe_refund_id, 're_updated_unverified_789')
        self.assertEqual(updated_refund_request.amount_to_refund, Decimal('120.00'))
        self.assertEqual(updated_refund_request.status, 'partially_refunded')
        self.assertEqual(updated_refund_request.processed_at, self.mock_now)
        self.assertIn("updated existing request", updated_refund_request.staff_notes)
        self.assertTrue(updated_refund_request.staff_notes.startswith(initial_notes))


    def test_payment_status_is_refunded_for_new_request(self):
        """
        Tests that if payment_obj.status is 'refunded', the new RefundRequest
        status is set to 'refunded'.
        """
        hire_booking = HireBookingFactory()
        # Simulate payment status as 'refunded' (full refund processed by Stripe)
        payment = PaymentFactory(hire_booking=hire_booking, status='refunded')
        
        extracted_data = {
            'stripe_refund_id': 're_full_refund_payment',
            'refunded_amount_decimal': Decimal('100.00'),
        }

        refund_request = process_refund_request_entry(payment, hire_booking, 'hire_booking', extracted_data)

        self.assertEqual(refund_request.status, 'refunded')
        self.assertEqual(refund_request.amount_to_refund, Decimal('100.00'))


    def test_payment_status_is_refunded_for_existing_request(self):
        """
        Tests that if payment_obj.status is 'refunded', an existing RefundRequest
        status is updated to 'refunded'.
        """
        service_booking = ServiceBookingFactory()
        # Simulate payment status as 'refunded'
        payment = PaymentFactory(service_booking=service_booking, status='refunded')
        
        existing_refund_request = RefundRequestFactory(
            payment=payment,
            service_booking=service_booking,
            status='pending', # Start with pending status
            amount_to_refund=Decimal('0.00'),
        )

        extracted_data = {
            'stripe_refund_id': 're_full_refund_existing',
            'refunded_amount_decimal': Decimal('150.00'),
        }

        updated_refund_request = process_refund_request_entry(payment, service_booking, 'service_booking', extracted_data)
        updated_refund_request.refresh_from_db()

        self.assertEqual(updated_refund_request.status, 'refunded')
        self.assertEqual(updated_refund_request.amount_to_refund, Decimal('150.00'))


    def test_no_booking_linked_to_payment(self):
        """
        Tests that if the payment_obj has no booking linked,
        the refund request also has no booking linked, but is still created.
        """
        payment = PaymentFactory(hire_booking=None, service_booking=None, status='succeeded')
        
        extracted_data = {
            'stripe_refund_id': 're_no_booking_linked',
            'refunded_amount_decimal': Decimal('25.00'),
        }

        refund_request = process_refund_request_entry(payment, None, 'unknown', extracted_data)

        self.assertIsNotNone(refund_request)
        self.assertEqual(refund_request.payment, payment)
        self.assertIsNone(refund_request.hire_booking)
        self.assertIsNone(refund_request.service_booking)
        self.assertEqual(refund_request.status, 'partially_refunded') # Payment status 'succeeded' -> 'partially_refunded'
        self.assertIn("initial creation", refund_request.staff_notes)

    def test_existing_refund_request_with_different_status_not_updated(self):
        """
        Tests that a RefundRequest with a status NOT in the filter list (e.g., 'refunded', 'rejected')
        does NOT get updated by the function, and a new one is created instead.
        NOTE: The current implementation creates a new request if no *matching* status is found.
        """
        hire_booking = HireBookingFactory()
        payment = PaymentFactory(hire_booking=hire_booking, status='succeeded')
        
        # Create an existing RefundRequest that is already 'refunded'
        # This one should NOT be picked up by the filter in process_refund_request_entry
        RefundRequestFactory(
            payment=payment,
            hire_booking=hire_booking,
            status='refunded', # This status is NOT in the filter list for updating
            amount_to_refund=Decimal('100.00'),
            stripe_refund_id='re_old_refunded',
            processed_at=self.mock_now - datetime.timedelta(days=2),
            staff_notes="Old refund already fully processed.",
            requested_at=self.mock_now - datetime.timedelta(days=3)
        )

        extracted_data = {
            'stripe_refund_id': 're_new_due_to_old_status',
            'refunded_amount_decimal': Decimal('50.00'),
        }

        # The function should create a NEW refund request here
        new_refund_request = process_refund_request_entry(payment, hire_booking, 'hire_booking', extracted_data)

        # Assertions for the NEWLY created RefundRequest
        self.assertIsNotNone(new_refund_request)
        # Verify it's a new object by checking its ID against the initial count
        self.assertEqual(payment.refund_requests.count(), 2) # Original + New
        self.assertEqual(new_refund_request.stripe_refund_id, 're_new_due_to_old_status')
        self.assertEqual(new_refund_request.amount_to_refund, Decimal('50.00'))
        self.assertEqual(new_refund_request.status, 'partially_refunded')
        self.assertIn("initial creation", new_refund_request.staff_notes)


    def test_existing_refund_request_with_failed_status_is_updated(self):
        """
        Tests that an existing RefundRequest with a 'failed' status is updated.
        """
        hire_booking = HireBookingFactory()
        payment = PaymentFactory(hire_booking=hire_booking, status='succeeded')
        
        # Create an existing RefundRequest in 'failed' status
        existing_refund_request = RefundRequestFactory(
            payment=payment,
            hire_booking=hire_booking,
            service_booking=None,
            status='failed',
            amount_to_refund=Decimal('0.00'), # Initial amount
            stripe_refund_id='re_failed_initial',
            processed_at=self.mock_now - datetime.timedelta(days=1),
            staff_notes="Refund failed previously.",
            requested_at=self.mock_now - datetime.timedelta(days=2)
        )
        initial_notes = existing_refund_request.staff_notes

        extracted_data = {
            'stripe_refund_id': 're_failed_updated_success',
            'refunded_amount_decimal': Decimal('80.00'),
        }

        updated_refund_request = process_refund_request_entry(payment, hire_booking, 'hire_booking', extracted_data)

        updated_refund_request.refresh_from_db()

        self.assertEqual(updated_refund_request.id, existing_refund_request.id)
        self.assertEqual(updated_refund_request.stripe_refund_id, 're_failed_updated_success')
        self.assertEqual(updated_refund_request.amount_to_refund, Decimal('80.00'))
        self.assertEqual(updated_refund_request.status, 'partially_refunded') # Payment status 'succeeded' -> 'partially_refunded'
        self.assertEqual(updated_refund_request.processed_at, self.mock_now)
        self.assertIn("updated existing request", updated_refund_request.staff_notes)
        self.assertTrue(updated_refund_request.staff_notes.startswith(initial_notes))
        # Ensure the count is still 1 (updated, not created new)
        self.assertEqual(payment.refund_requests.count(), 1)
