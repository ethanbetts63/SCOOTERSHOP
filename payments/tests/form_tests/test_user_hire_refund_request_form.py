# payments/tests/form_tests/test_user_hire_refund_request_form.py

from django.test import TestCase
from decimal import Decimal
from django.utils import timezone
from payments.forms.user_hire_refund_request_form import UserHireRefundRequestForm
from payments.models.HireRefundRequest import HireRefundRequest
from hire.tests.test_helpers.model_factories import (
    create_hire_booking,
    create_driver_profile,
    create_payment,
    create_user,
)
from hire.models import HireBooking # Import HireBooking to check its status

class UserHireRefundRequestFormTests(TestCase):
    """
    Tests for the UserHireRefundRequestForm.
    """

    def setUp(self):
        """Set up test data for all tests."""
        self.user = create_user(username='testuser', email='user@example.com')
        self.driver_profile = create_driver_profile(email='user@example.com')

        # Create a fully paid booking
        self.payment_paid = create_payment(
            amount=Decimal('500.00'),
            status='succeeded',
            driver_profile=self.driver_profile,
            stripe_payment_intent_id='pi_user_full_paid'
        )
        self.hire_booking_paid = create_hire_booking(
            driver_profile=self.driver_profile,
            payment=self.payment_paid,
            amount_paid=self.payment_paid.amount,
            grand_total=self.payment_paid.amount,
            payment_status='paid',
            status='confirmed',
            booking_reference='HIRE-FULLPAID',
            pickup_date=timezone.now().date() + timezone.timedelta(days=10),
            return_date=timezone.now().date() + timezone.timedelta(days=12),
        )
        self.payment_paid.hire_booking = self.hire_booking_paid
        self.payment_paid.save()

        # Create a deposit-paid booking
        self.payment_deposit = create_payment(
            amount=Decimal('100.00'),
            status='succeeded',
            driver_profile=self.driver_profile,
            stripe_payment_intent_id='pi_user_deposit_paid'
        )
        self.hire_booking_deposit = create_hire_booking(
            driver_profile=self.driver_profile,
            payment=self.payment_deposit,
            amount_paid=self.payment_deposit.amount,
            grand_total=Decimal('500.00'),
            deposit_amount=self.payment_deposit.amount,
            payment_status='deposit_paid',
            status='confirmed',
            booking_reference='HIRE-DEPOSIT',
            pickup_date=timezone.now().date() + timezone.timedelta(days=5),
            return_date=timezone.now().date() + timezone.timedelta(days=7),
        )
        self.payment_deposit.hire_booking = self.hire_booking_deposit
        self.payment_deposit.save()

        # Create an unpaid booking (should not be eligible for refund)
        self.hire_booking_unpaid = create_hire_booking(
            driver_profile=self.driver_profile,
            payment=None,
            amount_paid=Decimal('0.00'),
            grand_total=Decimal('300.00'),
            payment_status='unpaid',
            status='pending',
            booking_reference='HIRE-UNPAID',
            pickup_date=timezone.now().date() + timezone.timedelta(days=20),
            return_date=timezone.now().date() + timezone.timedelta(days=22),
        )

        # Create a booking with a different email for the driver profile
        self.driver_profile_other_email = create_driver_profile(email='other@example.com')
        self.payment_other_email = create_payment(
            amount=Decimal('200.00'),
            status='succeeded',
            driver_profile=self.driver_profile_other_email,
            stripe_payment_intent_id='pi_other_email'
        )
        self.hire_booking_other_email = create_hire_booking(
            driver_profile=self.driver_profile_other_email,
            payment=self.payment_other_email,
            amount_paid=self.payment_other_email.amount,
            grand_total=self.payment_other_email.amount,
            payment_status='paid',
            status='confirmed',
            booking_reference='HIRE-OTHEREMAIL',
            pickup_date=timezone.now().date() + timezone.timedelta(days=15),
            return_date=timezone.now().date() + timezone.timedelta(days=17),
        )
        self.payment_other_email.hire_booking = self.hire_booking_other_email
        self.payment_other_email.save()


    def test_form_valid_data_fully_paid(self):
        """
        Test that the form is valid with correct data for a fully paid booking.
        """
        form_data = {
            'booking_reference': self.hire_booking_paid.booking_reference,
            'email': self.driver_profile.email,
            'reason': 'Changed my mind, no longer need the bike.',
        }
        form = UserHireRefundRequestForm(data=form_data)
        self.assertTrue(form.is_valid(), f"Form is not valid: {form.errors}")

        refund_request = form.save()
        self.assertIsInstance(refund_request, HireRefundRequest)
        self.assertEqual(refund_request.hire_booking, self.hire_booking_paid)
        self.assertEqual(refund_request.payment, self.payment_paid)
        self.assertEqual(refund_request.driver_profile, self.driver_profile)
        self.assertEqual(refund_request.reason, 'Changed my mind, no longer need the bike.')
        self.assertEqual(refund_request.request_email, self.driver_profile.email.lower()) # Expect lowercase
        self.assertEqual(refund_request.status, 'unverified')
        self.assertFalse(refund_request.is_admin_initiated)
        self.assertIsNotNone(refund_request.requested_at)
        self.assertEqual(HireRefundRequest.objects.count(), 1)

    def test_form_valid_data_deposit_paid(self):
        """
        Test that the form is valid with correct data for a deposit-paid booking.
        """
        form_data = {
            'booking_reference': self.hire_booking_deposit.booking_reference,
            'email': self.driver_profile.email,
            'reason': 'Booking cancelled, requesting deposit refund.',
        }
        form = UserHireRefundRequestForm(data=form_data)
        self.assertTrue(form.is_valid(), f"Form is not valid: {form.errors}")

        refund_request = form.save()
        self.assertIsInstance(refund_request, HireRefundRequest)
        self.assertEqual(refund_request.hire_booking, self.hire_booking_deposit)
        self.assertEqual(refund_request.payment, self.payment_deposit)
        self.assertEqual(refund_request.driver_profile, self.driver_profile)
        self.assertEqual(refund_request.reason, 'Booking cancelled, requesting deposit refund.')
        self.assertEqual(refund_request.request_email, self.driver_profile.email.lower()) # Expect lowercase
        self.assertEqual(refund_request.status, 'unverified')
        self.assertFalse(refund_request.is_admin_initiated)
        self.assertEqual(HireRefundRequest.objects.count(), 1)

    def test_form_valid_data_no_reason(self):
        """
        Test that the form is valid when no reason is provided (optional field).
        """
        form_data = {
            'booking_reference': self.hire_booking_paid.booking_reference,
            'email': self.driver_profile.email,
            'reason': '', # Blank reason
        }
        form = UserHireRefundRequestForm(data=form_data)
        self.assertTrue(form.is_valid(), f"Form is not valid: {form.errors}")

        refund_request = form.save()
        self.assertEqual(refund_request.reason, '')
        self.assertEqual(HireRefundRequest.objects.count(), 1)

    def test_form_invalid_missing_booking_reference(self):
        """
        Test that the form is invalid if booking_reference is missing.
        """
        form_data = {
            'email': self.driver_profile.email,
            'reason': 'Missing booking ref.',
        }
        form = UserHireRefundRequestForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('booking_reference', form.errors)
        self.assertIn("This field is required.", form.errors['booking_reference'])

    def test_form_invalid_missing_email(self):
        """
        Test that the form is invalid if email is missing.
        """
        form_data = {
            'booking_reference': self.hire_booking_paid.booking_reference,
            'reason': 'Missing email.',
        }
        form = UserHireRefundRequestForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)
        self.assertIn("This field is required.", form.errors['email'])

    def test_form_invalid_booking_reference_not_found(self):
        """
        Test that the form is invalid if booking_reference does not exist.
        """
        form_data = {
            'booking_reference': 'HIRE-NONEXISTENT',
            'email': self.driver_profile.email,
            'reason': 'Invalid booking ref.',
        }
        form = UserHireRefundRequestForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('booking_reference', form.errors)
        self.assertIn("No booking found with this reference number.", form.errors['booking_reference'])

    def test_form_invalid_email_does_not_match(self):
        """
        Test that the form is invalid if the provided email does not match the booking's driver profile email.
        """
        form_data = {
            'booking_reference': self.hire_booking_paid.booking_reference,
            'email': 'wrong@example.com', # Incorrect email
            'reason': 'Email mismatch.',
        }
        form = UserHireRefundRequestForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)
        self.assertIn("The email address does not match the one registered for this booking.", form.errors['email'])

    def test_form_invalid_booking_not_eligible_unpaid(self):
        """
        Test that the form is invalid if the booking is unpaid.
        """
        form_data = {
            'booking_reference': self.hire_booking_unpaid.booking_reference,
            'email': self.driver_profile.email,
            'reason': 'Booking is unpaid.',
        }
        form = UserHireRefundRequestForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('booking_reference', form.errors)
        self.assertIn("This booking is not eligible for a refund (e.g., not paid or already cancelled).", form.errors['booking_reference'])

    def test_form_invalid_duplicate_active_refund_request(self):
        """
        Test that the form is invalid if an active refund request already exists for the booking.
        """
        # Create an existing unverified refund request for the paid booking
        HireRefundRequest.objects.create(
            hire_booking=self.hire_booking_paid,
            payment=self.payment_paid,
            driver_profile=self.driver_profile,
            reason='Existing request',
            status='unverified',
            is_admin_initiated=False,
            request_email=self.driver_profile.email
        )

        form_data = {
            'booking_reference': self.hire_booking_paid.booking_reference,
            'email': self.driver_profile.email,
            'reason': 'Attempting duplicate request.',
        }
        form = UserHireRefundRequestForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("A refund request for this booking is already in progress.", form.non_field_errors()) # Call the method


    def test_form_invalid_duplicate_active_refund_request_pending(self):
        """
        Test that the form is invalid if a pending refund request already exists.
        """
        # Create an existing pending refund request for the paid booking
        HireRefundRequest.objects.create(
            hire_booking=self.hire_booking_paid,
            payment=self.payment_paid,
            driver_profile=self.driver_profile,
            reason='Existing pending request',
            status='pending',
            is_admin_initiated=False,
            request_email=self.driver_profile.email
        )

        form_data = {
            'booking_reference': self.hire_booking_paid.booking_reference,
            'email': self.driver_profile.email,
            'reason': 'Attempting duplicate request.',
        }
        form = UserHireRefundRequestForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("A refund request for this booking is already in progress.", form.non_field_errors()) # Call the method

    def test_form_invalid_duplicate_active_refund_request_approved(self):
        """
        Test that the form is invalid if an approved refund request already exists.
        """
        # Create an existing approved refund request for the paid booking
        HireRefundRequest.objects.create(
            hire_booking=self.hire_booking_paid,
            payment=self.payment_paid,
            driver_profile=self.driver_profile,
            reason='Existing approved request',
            status='approved',
            is_admin_initiated=False,
            request_email=self.driver_profile.email
        )

        form_data = {
            'booking_reference': self.hire_booking_paid.booking_reference,
            'email': self.driver_profile.email,
            'reason': 'Attempting duplicate request.',
        }
        form = UserHireRefundRequestForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("A refund request for this booking is already in progress.", form.non_field_errors()) # Call the method

    def test_form_save_method_sets_correct_fields(self):
        """
        Test that the save method correctly sets the related fields and default status.
        """
        form_data = {
            'booking_reference': self.hire_booking_paid.booking_reference,
            'email': self.driver_profile.email,
            'reason': 'Testing save method.',
        }
        form = UserHireRefundRequestForm(data=form_data)
        self.assertTrue(form.is_valid())
        refund_request = form.save(commit=False) # Don't commit to DB yet

        self.assertEqual(refund_request.hire_booking, self.hire_booking_paid)
        self.assertEqual(refund_request.driver_profile, self.driver_profile)
        self.assertEqual(refund_request.payment, self.payment_paid)
        self.assertEqual(refund_request.status, 'unverified')
        self.assertFalse(refund_request.is_admin_initiated)
        self.assertEqual(refund_request.reason, 'Testing save method.')
        self.assertEqual(refund_request.request_email, self.driver_profile.email.lower()) # Expect lowercase

        refund_request.save() # Now save to DB
        self.assertEqual(HireRefundRequest.objects.count(), 1)
        retrieved_refund = HireRefundRequest.objects.first()
        self.assertEqual(retrieved_refund.hire_booking, self.hire_booking_paid)
        self.assertEqual(retrieved_refund.driver_profile, self.driver_profile)
        self.assertEqual(retrieved_refund.payment, self.payment_paid)
        self.assertEqual(retrieved_refund.status, 'unverified')
        self.assertFalse(retrieved_refund.is_admin_initiated)
        self.assertEqual(retrieved_refund.reason, 'Testing save method.')
        self.assertEqual(retrieved_refund.request_email, self.driver_profile.email.lower()) # Expect lowercase

    def test_form_clean_method_case_insensitivity(self):
        """
        Test that the clean method handles booking reference and email case-insensitively.
        """
        form_data = {
            'booking_reference': self.hire_booking_paid.booking_reference.lower(), # Lowercase booking ref
            'email': self.driver_profile.email.upper(), # Uppercase email
            'reason': 'Case insensitivity test.',
        }
        form = UserHireRefundRequestForm(data=form_data)
        self.assertTrue(form.is_valid(), f"Form is not valid: {form.errors}")

        refund_request = form.save()
        self.assertEqual(refund_request.hire_booking, self.hire_booking_paid)
        self.assertEqual(refund_request.request_email, self.driver_profile.email.lower()) # Expect lowercase
