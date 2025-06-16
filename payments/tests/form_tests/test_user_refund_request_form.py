# payments/tests/form_tests/test_user_refund_request_form.py

from django.test import TestCase
from decimal import Decimal

from payments.forms.user_refund_request_form import RefundRequestForm
from payments.models import RefundRequest
from payments.tests.test_helpers.model_factories import (
    PaymentFactory,
    HireBookingFactory,
    DriverProfileFactory,
    SalesBookingFactory,
    SalesProfileFactory,
    ServiceBookingFactory,
    ServiceProfileFactory,
    RefundRequestFactory,
    UserFactory
)

class UserRefundRequestFormTests(TestCase):
    """
    Tests for the user-facing RefundRequestForm.
    """

    def setUp(self):
        """Set up test data for all tests."""
        # Common user and profiles
        self.user = UserFactory()
        self.driver_profile = DriverProfileFactory(email='hire.customer@example.com')
        self.service_profile = ServiceProfileFactory(email='service.customer@example.com', user=self.user)
        self.sales_profile = SalesProfileFactory(email='sales.customer@example.com', user=self.user)

        # --- HIRE BOOKING SETUP ---
        payment_hire = PaymentFactory(
            status='succeeded',
            driver_profile=self.driver_profile,
            amount=Decimal('200.00')
        )
        self.hire_booking = HireBookingFactory(
            payment=payment_hire,
            driver_profile=self.driver_profile
        )
        payment_hire.hire_booking = self.hire_booking
        payment_hire.save()

        # --- SERVICE BOOKING SETUP ---
        payment_service = PaymentFactory(
            status='succeeded',
            service_customer_profile=self.service_profile,
            amount=Decimal('150.00')
        )
        self.service_booking = ServiceBookingFactory(
            payment=payment_service,
            service_profile=self.service_profile
        )
        payment_service.service_booking = self.service_booking
        payment_service.save()

        # --- SALES BOOKING SETUP ---
        payment_sales = PaymentFactory(
            status='succeeded',
            sales_customer_profile=self.sales_profile,
            amount=Decimal('500.00')
        )
        self.sales_booking = SalesBookingFactory(
            payment=payment_sales,
            sales_profile=self.sales_profile
        )
        payment_sales.sales_booking = self.sales_booking
        payment_sales.save()

    def test_valid_hire_booking_request(self):
        """Test a valid refund request for a HIRE booking."""
        form_data = {
            'booking_reference': self.hire_booking.booking_reference,
            'email': self.driver_profile.email,
            'reason': 'Test reason for hire refund.'
        }
        form = RefundRequestForm(data=form_data)
        self.assertTrue(form.is_valid(), f"Form should be valid but has errors: {form.errors.as_json()}")
        
        instance = form.save()
        self.assertIsNotNone(instance.pk)
        self.assertEqual(instance.payment, self.hire_booking.payment)
        self.assertEqual(instance.hire_booking, self.hire_booking)
        self.assertEqual(instance.driver_profile, self.driver_profile)
        self.assertEqual(instance.status, 'unverified')
        self.assertFalse(instance.is_admin_initiated)
        self.assertEqual(instance.reason, 'Test reason for hire refund.')
        self.assertEqual(instance.request_email, self.driver_profile.email.lower())
        # Ensure other booking types are None
        self.assertIsNone(instance.service_booking)
        self.assertIsNone(instance.sales_booking)

    def test_valid_service_booking_request(self):
        """Test a valid refund request for a SERVICE booking."""
        form_data = {
            'booking_reference': self.service_booking.service_booking_reference,
            'email': self.service_profile.email,
            'reason': 'Service was not as expected.'
        }
        form = RefundRequestForm(data=form_data)
        self.assertTrue(form.is_valid(), f"Form should be valid but has errors: {form.errors.as_json()}")
        
        instance = form.save()
        self.assertIsNotNone(instance.pk)
        self.assertEqual(instance.payment, self.service_booking.payment)
        self.assertEqual(instance.service_booking, self.service_booking)
        self.assertEqual(instance.service_profile, self.service_profile)
        self.assertEqual(instance.status, 'unverified')
        self.assertFalse(instance.is_admin_initiated)
        # Ensure other booking types are None
        self.assertIsNone(instance.hire_booking)
        self.assertIsNone(instance.sales_booking)

    def test_valid_sales_booking_request(self):
        """Test a valid refund request for a SALES booking."""
        form_data = {
            'booking_reference': self.sales_booking.sales_booking_reference,
            'email': self.sales_profile.email,
            'reason': 'Changed my mind about the purchase.'
        }
        form = RefundRequestForm(data=form_data)
        self.assertTrue(form.is_valid(), f"Form should be valid but has errors: {form.errors.as_json()}")

        instance = form.save()
        self.assertIsNotNone(instance.pk)
        self.assertEqual(instance.payment, self.sales_booking.payment)
        self.assertEqual(instance.sales_booking, self.sales_booking)
        self.assertEqual(instance.sales_profile, self.sales_profile)
        self.assertEqual(instance.status, 'unverified')
        self.assertFalse(instance.is_admin_initiated)
        # Ensure other booking types are None
        self.assertIsNone(instance.hire_booking)
        self.assertIsNone(instance.service_booking)
        
    def test_invalid_nonexistent_booking_reference(self):
        """Test form with a booking reference that does not exist."""
        form_data = {
            'booking_reference': 'HIRE-NONEXISTENT',
            'email': self.driver_profile.email,
            'reason': ''
        }
        form = RefundRequestForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('booking_reference', form.errors)
        self.assertEqual(form.errors['booking_reference'], ["No booking found with this reference number."])

    def test_invalid_email_mismatch(self):
        """Test form with a valid booking reference but an incorrect email."""
        form_data = {
            'booking_reference': self.hire_booking.booking_reference,
            'email': 'wrong.email@example.com',
            'reason': ''
        }
        form = RefundRequestForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)
        self.assertEqual(form.errors['email'], ["The email address does not match the one registered for this booking."])
        
    def test_invalid_case_insensitive_email_match(self):
        """Test email matching is case-insensitive."""
        form_data = {
            'booking_reference': self.hire_booking.booking_reference,
            'email': self.driver_profile.email.upper(), # Submit email in uppercase
            'reason': 'Testing case insensitivity.'
        }
        form = RefundRequestForm(data=form_data)
        self.assertTrue(form.is_valid(), f"Form should be valid but has errors: {form.errors.as_json()}")

    def test_invalid_booking_without_payment(self):
        """Test request for a booking that has no associated payment record."""
        hire_booking_no_payment = HireBookingFactory(driver_profile=self.driver_profile, payment=None)
        form_data = {
            'booking_reference': hire_booking_no_payment.booking_reference,
            'email': self.driver_profile.email,
            'reason': ''
        }
        form = RefundRequestForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('booking_reference', form.errors)
        self.assertEqual(form.errors['booking_reference'], ["No payment record found for this booking."])

    def test_invalid_payment_not_succeeded(self):
        """Test request for a booking where the payment status is not 'succeeded'."""
        payment_failed = PaymentFactory(status='failed', driver_profile=self.driver_profile)
        hire_booking_failed_payment = HireBookingFactory(driver_profile=self.driver_profile, payment=payment_failed)
        payment_failed.hire_booking = hire_booking_failed_payment
        payment_failed.save()

        form_data = {
            'booking_reference': hire_booking_failed_payment.booking_reference,
            'email': self.driver_profile.email,
            'reason': ''
        }
        form = RefundRequestForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('booking_reference', form.errors)
        self.assertEqual(form.errors['booking_reference'], ["This booking's payment is not in a 'succeeded' status and is not eligible for a refund."])

    def test_invalid_existing_pending_refund_request(self):
        """Test submitting a new request when one is already pending."""
        # Create an existing pending request
        RefundRequestFactory(payment=self.hire_booking.payment, status='pending')
        
        form_data = {
            'booking_reference': self.hire_booking.booking_reference,
            'email': self.driver_profile.email,
            'reason': 'Trying to submit again.'
        }
        form = RefundRequestForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('__all__', form.errors)
        self.assertEqual(form.errors['__all__'], ["A refund request for this booking is already in progress."])
        
    def test_valid_request_if_previous_is_rejected_or_failed(self):
        """Test a new request is allowed if a previous one was rejected or failed."""
        # Create a rejected request
        RefundRequestFactory(payment=self.hire_booking.payment, status='rejected')
        
        form_data = {
            'booking_reference': self.hire_booking.booking_reference,
            'email': self.driver_profile.email,
            'reason': 'Submitting after rejection.'
        }
        form = RefundRequestForm(data=form_data)
        self.assertTrue(form.is_valid(), f"Form should be valid after a rejection but has errors: {form.errors.as_json()}")
        
        # Create a failed request
        payment_for_failed = PaymentFactory(status='succeeded')
        hire_booking_for_failed = HireBookingFactory(payment=payment_for_failed, driver_profile=self.driver_profile)
        RefundRequestFactory(payment=payment_for_failed, status='failed')
        
        form_data_2 = {
            'booking_reference': hire_booking_for_failed.booking_reference,
            'email': self.driver_profile.email,
            'reason': 'Submitting after failure.'
        }
        form2 = RefundRequestForm(data=form_data_2)
        self.assertTrue(form2.is_valid(), f"Form should be valid after a failure but has errors: {form2.errors.as_json()}")

    def test_optional_reason_field(self):
        """Test that the reason field is optional and form is valid if it's empty."""
        form_data = {
            'booking_reference': self.hire_booking.booking_reference,
            'email': self.driver_profile.email,
            'reason': '' # Empty reason
        }
        form = RefundRequestForm(data=form_data)
        self.assertTrue(form.is_valid(), f"Form should be valid with an empty reason but has errors: {form.errors.as_json()}")
        instance = form.save()
        self.assertEqual(instance.reason, '')
