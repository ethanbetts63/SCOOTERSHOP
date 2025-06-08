# payments/tests/model_tests/test_hire_refund_request_model.py

from django.test import TestCase
from decimal import Decimal
from django.utils import timezone
import datetime # Import datetime for more precise time manipulation in tests

from payments.models.RefundRequest import HireRefundRequest
from payments.models.PaymentModel import Payment # Ensure PaymentModel is correctly imported
from hire.models import HireBooking, DriverProfile # Ensure HireBooking and DriverProfile are correctly imported
from hire.tests.test_helpers.model_factories import (
    create_hire_booking,
    create_driver_profile,
    create_payment,
    create_user,
)

class HireRefundRequestModelTests(TestCase):
    """
    Tests for the HireRefundRequest model.
    """

    def setUp(self):
        """Set up test data for all tests."""
        self.user = create_user(username='testuser', email='user@example.com')
        self.admin_user = create_user(username='adminuser', email='admin@example.com', is_staff=True)
        self.driver_profile = create_driver_profile(email='user@example.com')

        self.payment_succeeded = create_payment(
            amount=Decimal('500.00'),
            status='succeeded',
            driver_profile=self.driver_profile,
            stripe_payment_intent_id='pi_test_succeeded'
        )
        self.hire_booking_paid = create_hire_booking(
            driver_profile=self.driver_profile,
            payment=self.payment_succeeded,
            amount_paid=self.payment_succeeded.amount,
            grand_total=self.payment_succeeded.amount,
            payment_status='paid',
            status='confirmed',
            booking_reference='HIRE-MODELTEST',
            pickup_date=timezone.now().date() + timezone.timedelta(days=10),
            return_date=timezone.now().date() + timezone.timedelta(days=12),
        )
        # Link payment to hire booking after creation
        self.payment_succeeded.hire_booking = self.hire_booking_paid
        self.payment_succeeded.save()

    def test_hire_refund_request_creation(self):
        """
        Test that a HireRefundRequest instance can be created successfully with minimal valid data.
        """
        refund_request = HireRefundRequest.objects.create(
            hire_booking=self.hire_booking_paid,
            payment=self.payment_succeeded,
            driver_profile=self.driver_profile,
            reason="Customer cancelled booking.",
            request_email="customer@example.com",
            amount_to_refund=Decimal('500.00'),
            status='pending',
            is_admin_initiated=False,
        )

        self.assertIsInstance(refund_request, HireRefundRequest)
        self.assertEqual(refund_request.hire_booking, self.hire_booking_paid)
        self.assertEqual(refund_request.payment, self.payment_succeeded)
        self.assertEqual(refund_request.driver_profile, self.driver_profile)
        self.assertEqual(refund_request.reason, "Customer cancelled booking.")
        self.assertEqual(refund_request.request_email, "customer@example.com")
        self.assertEqual(refund_request.amount_to_refund, Decimal('500.00'))
        self.assertEqual(refund_request.status, 'pending')
        self.assertFalse(refund_request.is_admin_initiated)
        self.assertIsNotNone(refund_request.requested_at) # auto_now_add field
        self.assertIsNone(refund_request.processed_by)
        self.assertIsNone(refund_request.processed_at)
        self.assertEqual(refund_request.staff_notes, '')
        self.assertEqual(refund_request.stripe_refund_id, '')
        self.assertEqual(refund_request.refund_calculation_details, {})
        self.assertEqual(HireRefundRequest.objects.count(), 1)

    def test_hire_refund_request_default_values(self):
        """
        Test that default values are correctly applied when not provided.
        """
        refund_request = HireRefundRequest.objects.create(
            hire_booking=self.hire_booking_paid,
            payment=self.payment_succeeded,
            driver_profile=self.driver_profile,
            request_email="default@example.com", # request_email is required by form, but not by model directly
        )

        self.assertEqual(refund_request.status, 'unverified')
        self.assertFalse(refund_request.is_admin_initiated)
        self.assertEqual(refund_request.reason, '')
        self.assertIsNone(refund_request.amount_to_refund)
        self.assertEqual(refund_request.staff_notes, '')
        self.assertEqual(refund_request.stripe_refund_id, '')
        self.assertEqual(refund_request.refund_calculation_details, {})

    def test_relationships(self):
        """
        Test that the foreign key relationships are correctly established.
        """
        refund_request = HireRefundRequest.objects.create(
            hire_booking=self.hire_booking_paid,
            payment=self.payment_succeeded,
            driver_profile=self.driver_profile,
            request_email="test@example.com",
        )

        self.assertEqual(refund_request.hire_booking.booking_reference, 'HIRE-MODELTEST')
        self.assertEqual(refund_request.payment.amount, Decimal('500.00'))
        self.assertEqual(refund_request.driver_profile.email, 'user@example.com')

    def test_optional_fields_blank(self):
        """
        Test that optional fields can be left blank or null.
        """
        refund_request = HireRefundRequest.objects.create(
            hire_booking=self.hire_booking_paid,
            payment=self.payment_succeeded,
            driver_profile=self.driver_profile,
            request_email="optional@example.com",
            reason="",
            amount_to_refund=None,
            processed_by=None,
            processed_at=None,
            staff_notes="",
            stripe_refund_id="",
            refund_calculation_details={},
        )
        refund_request.refresh_from_db() # Ensure values are retrieved from DB

        self.assertEqual(refund_request.reason, '')
        self.assertIsNone(refund_request.amount_to_refund)
        self.assertIsNone(refund_request.processed_by)
        self.assertIsNone(refund_request.processed_at)
        self.assertEqual(refund_request.staff_notes, '')
        self.assertEqual(refund_request.stripe_refund_id, '')
        self.assertEqual(refund_request.refund_calculation_details, {})

    def test_status_choices(self):
        """
        Test that the status field correctly uses the defined choices.
        """
        # Test setting to various valid statuses
        for status_value, _ in HireRefundRequest.STATUS_CHOICES:
            with self.subTest(status=status_value):
                refund_request = HireRefundRequest.objects.create(
                    hire_booking=self.hire_booking_paid,
                    payment=self.payment_succeeded,
                    driver_profile=self.driver_profile,
                    request_email="status@example.com",
                    status=status_value
                )
                self.assertEqual(refund_request.status, status_value)
                refund_request.delete() # Clean up for next subtest

    def test_str_method(self):
        """
        Test the __str__ method of the model.
        """
        refund_request = HireRefundRequest.objects.create(
            hire_booking=self.hire_booking_paid,
            payment=self.payment_succeeded,
            driver_profile=self.driver_profile,
            request_email="str@example.com",
            status='refunded'
        )
        expected_str = f"Refund Request for Booking {self.hire_booking_paid.booking_reference} - Status: refunded"
        self.assertEqual(str(refund_request), expected_str)

        # Removed the test case for hire_booking=None as it's not allowed by the model's NOT NULL constraint.

    def test_admin_initiated_flag(self):
        """
        Test the is_admin_initiated flag.
        """
        user_initiated_refund = HireRefundRequest.objects.create(
            hire_booking=self.hire_booking_paid,
            payment=self.payment_succeeded,
            driver_profile=self.driver_profile,
            request_email="user_init@example.com",
            is_admin_initiated=False,
        )
        self.assertFalse(user_initiated_refund.is_admin_initiated)

        admin_initiated_refund = HireRefundRequest.objects.create(
            hire_booking=self.hire_booking_paid,
            payment=self.payment_succeeded,
            driver_profile=self.driver_profile,
            request_email="admin_init@example.com",
            is_admin_initiated=True,
            processed_by=self.admin_user,
            processed_at=timezone.now(),
            staff_notes="Admin created this refund."
        )
        self.assertTrue(admin_initiated_refund.is_admin_initiated)
        self.assertEqual(admin_initiated_refund.processed_by, self.admin_user)
        self.assertIsNotNone(admin_initiated_refund.processed_at)
        self.assertEqual(admin_initiated_refund.staff_notes, "Admin created this refund.")

    