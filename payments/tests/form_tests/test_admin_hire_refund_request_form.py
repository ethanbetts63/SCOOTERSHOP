# payments/tests/form_tests/test_admin_hire_refund_request_form.py

from django.test import TestCase
from decimal import Decimal
from payments.forms.admin_hire_refund_request_form import AdminHireRefundRequestForm
from hire.tests.test_helpers.model_factories import (
    create_hire_booking,
    create_driver_profile,
    create_payment,
    create_user,
)
from payments.models.HireRefundRequest import HireRefundRequest # Corrected model import
from payments.models.PaymentModel import Payment
from hire.models import HireBooking
from django.utils import timezone


class AdminHireRefundRequestFormTests(TestCase):
    """
    Tests for the AdminHireRefundRequestForm.
    """

    def setUp(self):
        """Set up test data for all tests."""
        self.admin_user = create_user(username='admin', email='admin@example.com', is_staff=True)
        self.driver_profile = create_driver_profile(email='test@example.com')
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
            pickup_date=timezone.now().date() + timezone.timedelta(days=10),
            return_date=timezone.now().date() + timezone.timedelta(days=12),
        )
        # Link payment to hire booking after creation
        self.payment_succeeded.hire_booking = self.hire_booking_paid
        self.payment_succeeded.save()

        self.payment_deposit_paid = create_payment(
            amount=Decimal('100.00'),
            status='succeeded',
            driver_profile=self.driver_profile,
            stripe_payment_intent_id='pi_test_deposit'
        )
        self.hire_booking_deposit = create_hire_booking(
            driver_profile=self.driver_profile,
            payment=self.payment_deposit_paid,
            amount_paid=self.payment_deposit_paid.amount,
            grand_total=Decimal('500.00'), # Grand total is higher than deposit
            deposit_amount=self.payment_deposit_paid.amount,
            payment_status='deposit_paid',
            status='confirmed',
            pickup_date=timezone.now().date() + timezone.timedelta(days=5),
            return_date=timezone.now().date() + timezone.timedelta(days=7),
        )
        self.payment_deposit_paid.hire_booking = self.hire_booking_deposit
        self.payment_deposit_paid.save()

        # This booking is unpaid and will not appear in the ModelChoiceField's queryset
        self.hire_booking_unpaid = create_hire_booking(
            driver_profile=self.driver_profile,
            payment=None, # No payment linked
            amount_paid=Decimal('0.00'),
            grand_total=Decimal('300.00'),
            payment_status='unpaid',
            status='pending',
            pickup_date=timezone.now().date() + timezone.timedelta(days=20),
            return_date=timezone.now().date() + timezone.timedelta(days=22),
        )

    def test_form_valid_data_create(self):
        """
        Test that the form is valid with correct data for creating a new request.
        """
        form_data = {
            'hire_booking': self.hire_booking_paid.pk,
            'reason': 'Customer requested full refund.',
            'staff_notes': 'Processed as per policy.',
            'amount_to_refund': '500.00',
            'is_admin_initiated': True,
            'status': 'pending',
        }
        form = AdminHireRefundRequestForm(data=form_data)
        self.assertTrue(form.is_valid(), f"Form is not valid: {form.errors}")

        refund_request = form.save()
        self.assertIsInstance(refund_request, HireRefundRequest) # Corrected model reference
        self.assertEqual(refund_request.hire_booking, self.hire_booking_paid)
        self.assertEqual(refund_request.payment, self.payment_succeeded)
        self.assertEqual(refund_request.driver_profile, self.driver_profile)
        self.assertEqual(refund_request.reason, 'Customer requested full refund.')
        self.assertEqual(refund_request.staff_notes, 'Processed as per policy.')
        self.assertEqual(refund_request.amount_to_refund, Decimal('500.00'))
        self.assertTrue(refund_request.is_admin_initiated)
        self.assertEqual(refund_request.status, 'pending')
        self.assertIsNotNone(refund_request.requested_at)
        self.assertEqual(HireRefundRequest.objects.count(), 1) # Corrected model reference

    def test_form_valid_data_deposit_paid(self):
        """
        Test that the form is valid for a deposit-paid booking.
        """
        form_data = {
            'hire_booking': self.hire_booking_deposit.pk,
            'reason': 'Customer requested deposit refund.',
            'staff_notes': 'Deposit refund initiated.',
            'amount_to_refund': '100.00',
            'is_admin_initiated': True,
            'status': 'approved',
        }
        form = AdminHireRefundRequestForm(data=form_data)
        self.assertTrue(form.is_valid(), f"Form is not valid: {form.errors}")

        refund_request = form.save()
        self.assertIsInstance(refund_request, HireRefundRequest) # Corrected model reference
        self.assertEqual(refund_request.hire_booking, self.hire_booking_deposit)
        self.assertEqual(refund_request.payment, self.payment_deposit_paid)
        self.assertEqual(refund_request.driver_profile, self.driver_profile)
        self.assertEqual(refund_request.amount_to_refund, Decimal('100.00'))
        self.assertEqual(refund_request.status, 'approved')

    def test_form_invalid_no_hire_booking(self):
        """
        Test that the form is invalid if no hire_booking is provided.
        """
        form_data = {
            'reason': 'Test reason',
            'staff_notes': 'Test notes',
            'amount_to_refund': '100.00',
            'is_admin_initiated': True,
            'status': 'pending',
        }
        form = AdminHireRefundRequestForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('hire_booking', form.errors)

    def test_form_invalid_amount_exceeds_paid(self):
        """
        Test that the form is invalid if amount_to_refund exceeds amount_paid.
        """
        form_data = {
            'hire_booking': self.hire_booking_paid.pk,
            'reason': 'Customer requested too much.',
            'staff_notes': 'Amount too high.',
            'amount_to_refund': '500.01', # Exceeds paid amount
            'is_admin_initiated': True,
            'status': 'pending',
        }
        form = AdminHireRefundRequestForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('amount_to_refund', form.errors)
        self.assertIn("cannot exceed the amount paid", form.errors['amount_to_refund'][0])

    def test_form_invalid_negative_amount(self):
        """
        Test that the form is invalid if amount_to_refund is negative.
        """
        form_data = {
            'hire_booking': self.hire_booking_paid.pk,
            'reason': 'Test reason',
            'staff_notes': 'Test notes',
            'amount_to_refund': '-10.00',
            'is_admin_initiated': True,
            'status': 'pending',
        }
        form = AdminHireRefundRequestForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('amount_to_refund', form.errors)
        self.assertIn("must be a positive value", form.errors['amount_to_refund'][0])

    def test_form_invalid_booking_without_payment(self):
        """
        Test that the form is invalid if the selected booking is not in the queryset (e.g., unpaid).
        The form's ModelChoiceField will raise a "Select a valid choice" error.
        """
        form_data = {
            'hire_booking': self.hire_booking_unpaid.pk, # This booking is not in the queryset
            'reason': 'Booking not paid.',
            'staff_notes': 'No payment.',
            'amount_to_refund': '10.00',
            'is_admin_initiated': True,
            'status': 'pending',
        }
        form = AdminHireRefundRequestForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('hire_booking', form.errors)
        # Assert the specific error message from ModelChoiceField
        self.assertIn("Select a valid choice. That choice is not one of the available choices.", form.errors['hire_booking'])


    def test_form_initial_values_for_new_instance(self):
        """
        Test that initial values like is_admin_initiated and status are set correctly for new forms.
        """
        form = AdminHireRefundRequestForm()
        self.assertTrue(form.initial.get('is_admin_initiated'))
        self.assertEqual(form.initial.get('status'), 'pending')

    def test_form_edit_instance(self):
        """
        Test that the form correctly loads and saves an existing instance.
        """
        existing_refund_request = HireRefundRequest.objects.create( # Corrected model reference
            hire_booking=self.hire_booking_paid,
            payment=self.payment_succeeded,
            driver_profile=self.driver_profile,
            reason='Original reason',
            staff_notes='Original notes',
            amount_to_refund=Decimal('250.00'),
            is_admin_initiated=True,
            status='pending',
        )

        form_data = {
            'hire_booking': self.hire_booking_paid.pk, # Must be provided even for edit
            'reason': 'Updated reason',
            'staff_notes': 'Updated notes.',
            'amount_to_refund': '300.00',
            'is_admin_initiated': True,
            'status': 'approved',
        }
        form = AdminHireRefundRequestForm(data=form_data, instance=existing_refund_request)
        self.assertTrue(form.is_valid(), f"Form is not valid: {form.errors}")

        updated_refund_request = form.save()
        self.assertEqual(updated_refund_request.pk, existing_refund_request.pk)
        self.assertEqual(updated_refund_request.reason, 'Updated reason')
        self.assertEqual(updated_refund_request.staff_notes, 'Updated notes.')
        self.assertEqual(updated_refund_request.amount_to_refund, Decimal('300.00'))
        self.assertEqual(updated_refund_request.status, 'approved')
        self.assertEqual(HireRefundRequest.objects.count(), 1) # Corrected model reference

    def test_form_optional_fields_blank(self):
        """
        Test that the form is valid when optional fields are left blank.
        For DecimalField, passing None is appropriate for blank.
        """
        form_data = {
            'hire_booking': self.hire_booking_paid.pk,
            'reason': '', # Blank
            'staff_notes': '', # Blank
            'amount_to_refund': None, # Changed from '' to None for DecimalField
            'is_admin_initiated': True,
            'status': 'pending',
        }
        form = AdminHireRefundRequestForm(data=form_data)
        self.assertTrue(form.is_valid(), f"Form is not valid: {form.errors}")
        refund_request = form.save()
        self.assertEqual(refund_request.reason, '')
        self.assertEqual(refund_request.staff_notes, '')
        self.assertIsNone(refund_request.amount_to_refund) # Should be None if None in form data
