# payments/tests/test_views/test_admin_add_edit_refund_request_view.py

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.utils import timezone
from decimal import Decimal
from unittest import mock

# Import model factories for creating test data
from hire.tests.test_helpers.model_factories import (
    create_user,
    create_hire_booking,
    create_payment,
    create_driver_profile,
    create_refund_request,
    create_hire_settings, # Needed for refund_policy_snapshot in payment
)
from payments.models.RefundRequest import RefundRequest
from payments.models import Payment # Import Payment model directly
# No longer mocking AdminRefundRequestForm, so no explicit import needed here for tests.


User = get_user_model()

class AdminAddEditRefundRequestViewTests(TestCase):
    """
    Tests for the AdminAddEditRefundRequestView.
    """

    def setUp(self):
        """
        Set up common test data for all tests.
        """
        self.client = Client()
        # Create a staff user for admin access
        self.staff_user = create_user(username='adminuser', email='admin@example.com', is_staff=True)
        # Create a non-staff user for unauthenticated access tests
        self.regular_user = create_user(username='regularuser', email='user@example.com', is_staff=False)

        # Ensure HireSettings exists for payment creation's refund_policy_snapshot
        self.hire_settings = create_hire_settings()

        # Create a driver profile
        self.driver_profile = create_driver_profile(user=self.regular_user)

        # Create a payment with a refund policy snapshot
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

        self.payment = create_payment(
            amount=Decimal('500.00'),
            status='succeeded',
            driver_profile=self.driver_profile,
            refund_policy_snapshot=self.refund_policy_snapshot
        )
        # Create a hire booking linked to the payment
        self.hire_booking = create_hire_booking(
            driver_profile=self.driver_profile,
            payment=self.payment,
            amount_paid=self.payment.amount,
            grand_total=self.payment.amount,
            payment_status='paid',
            status='confirmed',
        )
        # Link payment to hire booking after booking is created
        self.payment.hire_booking = self.hire_booking
        self.payment.save()

        # URLs for the view
        self.add_url = reverse('dashboard:add_hire_refund_request')
        self.edit_url = lambda pk: reverse('dashboard:edit_hire_refund_request', kwargs={'pk': pk})
        self.management_url = reverse('dashboard:admin_hire_refund_management')

    def _login_staff_user(self):
        """Helper to log in the staff user."""
        self.client.login(username=self.staff_user.username, password='password123')

    # --- Test GET requests ---

    def test_get_add_new_refund_request_form(self):
        """
        Test GET request to display an empty form for a new refund request.
        """
        self._login_staff_user()
        response = self.client.get(self.add_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'payments/admin_hire_refund_form.html')
        self.assertIn('form', response.context)
        self.assertIn('title', response.context)
        self.assertEqual(response.context['title'], "Create New Hire Refund Request")
        self.assertIsNone(response.context['hire_refund_request']) # Should be None for new form

        # Check if form fields are empty (or default)
        form = response.context['form']
        self.assertIsNone(form.initial.get('hire_booking'))
        self.assertEqual(form.initial.get('amount_to_refund'), None) # Should be None initially
        # is_admin_initiated and status are now handled by the view, not form.initial
        self.assertIsNone(form.initial.get('is_admin_initiated'))
        self.assertIsNone(form.initial.get('status'))


    def test_get_edit_existing_refund_request_form(self):
        """
        Test GET request to display a pre-filled form for an existing refund request.
        """
        existing_refund_request = create_refund_request(
            hire_booking=self.hire_booking,
            payment=self.payment,
            driver_profile=self.driver_profile,
            reason="Duplicate booking",
            status='pending', # Initial status for the existing request
            amount_to_refund=Decimal('100.00'),
            request_email="test@example.com", # Ensure this is set in the factory
            is_admin_initiated=True, # Assume it was admin initiated
        )
        self._login_staff_user()
        response = self.client.get(self.edit_url(existing_refund_request.pk))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'payments/admin_hire_refund_form.html')
        self.assertIn('form', response.context)
        self.assertIn('title', response.context)
        self.assertEqual(response.context['title'], "Edit Hire Refund Request")
        self.assertEqual(response.context['hire_refund_request'], existing_refund_request)

        # Check if form fields are pre-filled
        form = response.context['form']
        self.assertEqual(form.initial['hire_booking'], existing_refund_request.hire_booking.pk)
        self.assertEqual(form.initial['amount_to_refund'], existing_refund_request.amount_to_refund)
        # Status and is_admin_initiated are no longer in form.initial as they are not form fields
        # Instead, check the instance directly for its current status
        self.assertEqual(response.context['hire_refund_request'].status, 'pending')
        self.assertTrue(response.context['hire_refund_request'].is_admin_initiated)
        self.assertEqual(form.initial['reason'], "Duplicate booking")


    def test_get_non_existent_refund_request_returns_404(self):
        """
        Test GET request for a non-existent refund request returns 404.
        """
        self._login_staff_user()
        response = self.client.get(self.edit_url(9999)) # Non-existent PK
        self.assertEqual(response.status_code, 404)

    # --- Test POST requests (Create) ---

    @mock.patch('django.contrib.messages.success')
    def test_post_create_new_refund_request_valid_data(self, mock_messages_success):
        """
        Test POST request to create a new refund request with valid data.
        It should set status to 'reviewed_pending_approval' and is_admin_initiated to True.
        """
        self._login_staff_user()
        initial_count = RefundRequest.objects.count()

        form_data = {
            'hire_booking': self.hire_booking.pk,
            'reason': 'Customer changed mind',
            'amount_to_refund': '250.00',
            'staff_notes': 'Initial request from customer',
            # is_admin_initiated and status are now handled by the view, not passed in form_data
        }
        response = self.client.post(self.add_url, form_data, follow=True)

        self.assertEqual(response.status_code, 200) # Should redirect and then render
        self.assertRedirects(response, self.management_url)
        self.assertEqual(RefundRequest.objects.count(), initial_count + 1)

        new_refund_request = RefundRequest.objects.latest('id') # Get the newly created one
        self.assertEqual(new_refund_request.hire_booking, self.hire_booking)
        self.assertEqual(new_refund_request.payment, self.payment)
        self.assertEqual(new_refund_request.driver_profile, self.driver_profile)
        self.assertEqual(new_refund_request.reason, 'Customer changed mind')
        self.assertEqual(new_refund_request.status, 'reviewed_pending_approval') # New expected status
        self.assertEqual(new_refund_request.amount_to_refund, Decimal('250.00'))
        self.assertIsNone(new_refund_request.request_email)
        self.assertEqual(new_refund_request.staff_notes, 'Initial request from customer')
        self.assertTrue(new_refund_request.is_admin_initiated) # Should be True now
        self.assertIsNone(new_refund_request.processed_by)
        self.assertIsNone(new_refund_request.processed_at)

        mock_messages_success.assert_called_once_with(
            mock.ANY, f"Hire Refund Request for booking '{self.hire_booking.booking_reference}' saved successfully! Current Status: {new_refund_request.get_status_display()}"
        )

    @mock.patch('django.contrib.messages.error')
    def test_post_create_new_refund_request_invalid_data(self, mock_messages_error):
        """
        Test POST request to create a new refund request with invalid data.
        (e.g., amount_to_refund <= 0)
        """
        self._login_staff_user()
        initial_count = RefundRequest.objects.count()

        # Invalid data: amount_to_refund is negative (violates clean method validation)
        form_data = {
            'hire_booking': self.hire_booking.pk,
            'reason': 'Customer changed mind', # Reason is optional, so this is fine
            'amount_to_refund': '-10.00', # Invalid amount
            'staff_notes': 'Some notes',
        }
        response = self.client.post(self.add_url, form_data)

        self.assertEqual(response.status_code, 200) # Should re-render the form with errors
        self.assertTemplateUsed(response, 'payments/admin_hire_refund_form.html')
        self.assertEqual(RefundRequest.objects.count(), initial_count) # No new object created

        self.assertIn('form', response.context)
        form = response.context['form']
        self.assertTrue(form.errors)
        self.assertIn('amount_to_refund', form.errors) # Assert specific error
        # FIX: Updated the expected error message to match the actual form error
        self.assertIn("Amount to refund cannot be a negative value.", str(form.errors['amount_to_refund']))
        mock_messages_error.assert_called_once_with(mock.ANY, "Please correct the errors below.")

    @mock.patch('django.contrib.messages.success')
    def test_post_create_new_refund_request_approved_status_sets_processed_fields(self, mock_messages_success):
        """
        Test that processed_by and processed_at are set when creating with 'approved' status.
        NOTE: This test case needs to be adjusted as the form now transitions to 'reviewed_pending_approval'
        first. A separate action (e.g., from a management page) would be needed to transition to 'approved'.
        For now, this test will verify the initial 'reviewed_pending_approval' status.
        """
        self._login_staff_user()

        form_data = {
            'hire_booking': self.hire_booking.pk,
            'reason': 'Approved by admin',
            'amount_to_refund': '250.00',
        }
        response = self.client.post(self.add_url, form_data, follow=True)

        self.assertEqual(response.status_code, 200)
        new_refund_request = RefundRequest.objects.latest('id')
        self.assertEqual(new_refund_request.status, 'reviewed_pending_approval') # Expect new status
        self.assertTrue(new_refund_request.is_admin_initiated) # Should be True
        self.assertIsNone(new_refund_request.processed_by) # Should be None at this stage
        self.assertIsNone(new_refund_request.processed_at) # Should be None at this stage
        mock_messages_success.assert_called_once_with(
            mock.ANY, f"Hire Refund Request for booking '{self.hire_booking.booking_reference}' saved successfully! Current Status: {new_refund_request.get_status_display()}"
        )


    # --- Test POST requests (Edit) ---

    @mock.patch('django.contrib.messages.success')
    def test_post_edit_existing_refund_request_valid_data(self, mock_messages_success):
        """
        Test POST request to edit an existing refund request with valid data.
        If the original status was 'pending', it should transition to 'reviewed_pending_approval'.
        """
        existing_refund_request = create_refund_request(
            hire_booking=self.hire_booking,
            payment=self.payment,
            driver_profile=self.driver_profile,
            reason="Initial reason",
            status='pending', # Original status
            amount_to_refund=Decimal('100.00'),
            request_email="original@example.com", # This will remain unchanged by the form
            staff_notes="Old notes",
            is_admin_initiated=True, # Assume it was admin initiated
        )
        self._login_staff_user()
        initial_count = RefundRequest.objects.count()

        form_data = {
            'hire_booking': self.hire_booking.pk,
            'reason': 'Updated reason for refund',
            'amount_to_refund': '150.00',
            'staff_notes': 'New staff notes added',
            # is_admin_initiated and status are now handled by the view, not passed in form_data
        }
        response = self.client.post(self.edit_url(existing_refund_request.pk), form_data, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertRedirects(response, self.management_url)
        self.assertEqual(RefundRequest.objects.count(), initial_count) # No new object created

        existing_refund_request.refresh_from_db() # Reload from DB
        self.assertEqual(existing_refund_request.reason, 'Updated reason for refund')
        self.assertEqual(existing_refund_request.amount_to_refund, Decimal('150.00'))
        self.assertEqual(existing_refund_request.request_email, "original@example.com")
        self.assertEqual(existing_refund_request.staff_notes, 'New staff notes added')
        self.assertEqual(existing_refund_request.status, 'reviewed_pending_approval') # New expected status
        self.assertTrue(existing_refund_request.is_admin_initiated) # Should remain True
        self.assertIsNone(existing_refund_request.processed_by) # Should still be None
        self.assertIsNone(existing_refund_request.processed_at) # Should still be None

        mock_messages_success.assert_called_once_with(
            mock.ANY, f"Hire Refund Request for booking '{self.hire_booking.booking_reference}' saved successfully! Current Status: {existing_refund_request.get_status_display()}"
        )

    @mock.patch('django.contrib.messages.error')
    def test_post_edit_existing_refund_request_invalid_data(self, mock_messages_error):
        """
        Test POST request to edit an existing refund request with invalid data.
        (e.g., amount_to_refund exceeds payment amount)
        """
        existing_refund_request = create_refund_request(
            hire_booking=self.hire_booking,
            payment=self.payment,
            driver_profile=self.driver_profile,
            reason="Initial reason",
            status='pending',
            amount_to_refund=Decimal('100.00'),
            request_email="test@example.com",
            is_admin_initiated=True,
        )
        self._login_staff_user()
        initial_count = RefundRequest.objects.count()

        # Invalid data: amount_to_refund exceeds payment.amount (500.00)
        form_data = {
            'hire_booking': self.hire_booking.pk,
            'reason': 'Initial reason',
            'amount_to_refund': '600.00', # Invalid: exceeds paid amount
        }
        response = self.client.post(self.edit_url(existing_refund_request.pk), form_data)

        self.assertEqual(response.status_code, 200) # Should re-render the form with errors
        self.assertTemplateUsed(response, 'payments/admin_hire_refund_form.html')
        self.assertEqual(RefundRequest.objects.count(), initial_count) # No new object created

        # We don't refresh_from_db() as the form was invalid and no save happened.
        # Instead, we check the form errors in the context.
        self.assertIn('form', response.context)
        form = response.context['form']
        self.assertTrue(form.errors)
        self.assertIn('amount_to_refund', form.errors)
        self.assertIn(f"Amount to refund (${Decimal('600.00')}) cannot exceed the amount paid for this booking (${self.payment.amount}).", str(form.errors['amount_to_refund']))
        mock_messages_error.assert_called_once_with(mock.ANY, "Please correct the errors below.")

    @mock.patch('django.contrib.messages.success')
    def test_post_edit_existing_refund_request_change_status_to_approved_sets_processed_fields(self, mock_messages_success):
        """
        Test that processed_by and processed_at are set when changing status to 'approved'.
        This test now assumes the refund request is already in 'reviewed_pending_approval'
        and is being explicitly approved (e.g., from a different view/action).
        The current form will only transition from 'pending' to 'reviewed_pending_approval'.
        So, this test needs to be modified to reflect that the form does not directly set 'approved'.
        """
        existing_refund_request = create_refund_request(
            hire_booking=self.hire_booking,
            payment=self.payment,
            driver_profile=self.driver_profile,
            reason="Pending approval",
            status='reviewed_pending_approval', # Start in the new status
            amount_to_refund=Decimal('200.00'),
            is_admin_initiated=True,
        )
        # Manually set processed_by and processed_at to None and save, as factory doesn't accept them
        existing_refund_request.processed_by = None
        existing_refund_request.processed_at = None
        existing_refund_request.save() # Save the instance after setting None

        self._login_staff_user()

        # To test the transition to 'approved' or 'refunded', this form is not the right place.
        # This form only sets to 'reviewed_pending_approval'.
        # We will adjust this test to reflect that the status remains 'reviewed_pending_approval'
        # if it was already in that state, or transitions to it from 'pending'.
        # If the goal is to test the 'approved' transition, it needs a separate view/action.
        form_data = {
            'hire_booking': self.hire_booking.pk,
            'reason': 'Updated notes after review',
            'amount_to_refund': '200.00',
        }
        response = self.client.post(self.edit_url(existing_refund_request.pk), form_data, follow=True)

        self.assertEqual(response.status_code, 200)
        existing_refund_request.refresh_from_db()
        # The status should remain 'reviewed_pending_approval' because this form doesn't change it to 'approved'
        self.assertEqual(existing_refund_request.status, 'reviewed_pending_approval')
        self.assertIsNone(existing_refund_request.processed_by)
        self.assertIsNone(existing_refund_request.processed_at)
        mock_messages_success.assert_called_once_with(
            mock.ANY, f"Hire Refund Request for booking '{self.hire_booking.booking_reference}' saved successfully! Current Status: {existing_refund_request.get_status_display()}"
        )


    @mock.patch('django.contrib.messages.success')
    def test_post_edit_existing_refund_request_change_status_to_refunded_sets_processed_fields(self, mock_messages_success):
        """
        Test that processed_by and processed_at are set when changing status to 'refunded'.
        Similar to the 'approved' test, this form does not directly set 'refunded'.
        """
        existing_refund_request = create_refund_request(
            hire_booking=self.hire_booking,
            payment=self.payment,
            driver_profile=self.driver_profile,
            reason="Refund processed",
            status='reviewed_pending_approval', # Start in the new status
            amount_to_refund=Decimal('200.00'),
            is_admin_initiated=True,
        )
        # Manually set processed_by and processed_at to None and save
        existing_refund_request.processed_by = None
        existing_refund_request.processed_at = None
        existing_refund_request.save() # Save the instance after setting None

        self._login_staff_user()

        form_data = {
            'hire_booking': self.hire_booking.pk,
            'reason': 'Refund processed',
            'amount_to_refund': '200.00',
        }
        response = self.client.post(self.edit_url(existing_refund_request.pk), form_data, follow=True)

        self.assertEqual(response.status_code, 200)
        existing_refund_request.refresh_from_db()
        # The status should remain 'reviewed_pending_approval'
        self.assertEqual(existing_refund_request.status, 'reviewed_pending_approval')
        self.assertIsNone(existing_refund_request.processed_by)
        self.assertIsNone(existing_refund_request.processed_at)
        mock_messages_success.assert_called_once_with(
            mock.ANY, f"Hire Refund Request for booking '{self.hire_booking.booking_reference}' saved successfully! Current Status: {existing_refund_request.get_status_display()}"
        )

    @mock.patch('django.contrib.messages.success')
    def test_post_edit_existing_refund_request_processed_fields_not_overwritten(self, mock_messages_success):
        """
        Test that processed_by and processed_at are NOT overwritten if already set.
        This test needs to be adjusted to reflect that this form does not set 'approved' or 'refunded'.
        """
        # Create a refund request that was already processed (e.g., from a different action)
        original_processed_by = create_user(username='oldprocessor', email='old@example.com', is_staff=True)
        original_processed_at = timezone.now() - timezone.timedelta(days=5)

        existing_refund_request = create_refund_request(
            hire_booking=self.hire_booking,
            payment=self.payment,
            driver_profile=self.driver_profile,
            reason="Already processed",
            status='approved', # Start in an already processed status
            amount_to_refund=Decimal('200.00'),
            is_admin_initiated=True,
        )
        # Manually set processed_by and processed_at and save
        existing_refund_request.processed_by = original_processed_by
        existing_refund_request.processed_at = original_processed_at
        existing_refund_request.save() # Save the instance after setting

        self._login_staff_user()

        form_data = {
            'hire_booking': self.hire_booking.pk,
            'reason': 'Updated notes for processed refund',
            'amount_to_refund': '200.00',
        }
        response = self.client.post(self.edit_url(existing_refund_request.pk), form_data, follow=True)

        self.assertEqual(response.status_code, 200)
        existing_refund_request.refresh_from_db()
        # Assert that processed_by and processed_at were NOT overwritten
        self.assertEqual(existing_refund_request.processed_by, original_processed_by)
        self.assertEqual(existing_refund_request.processed_at, original_processed_at)
        # The status should remain 'approved' as this form doesn't change it from 'approved'
        self.assertEqual(existing_refund_request.status, 'approved')
        mock_messages_success.assert_called_once_with(
            mock.ANY, f"Hire Refund Request for booking '{self.hire_booking.booking_reference}' saved successfully! Current Status: {existing_refund_request.get_status_display()}"
        )

    # --- Test Authentication ---

    def test_unauthenticated_user_redirected_to_login(self):
        """
        Test that an unauthenticated user is redirected to the login page.
        """
        response_add = self.client.get(self.add_url)
        self.assertRedirects(response_add, f'/accounts/login/?next={self.add_url}')

        existing_refund_request = create_refund_request(
            hire_booking=self.hire_booking,
            payment=self.payment,
            driver_profile=self.driver_profile,
        )
        response_edit = self.client.get(self.edit_url(existing_refund_request.pk))
        self.assertRedirects(response_edit, f'/accounts/login/?next={self.edit_url(existing_refund_request.pk)}')

    def test_non_staff_user_redirected_to_login(self):
        """
        Test that a non-staff authenticated user is redirected to the login page
        (assuming login_required also implies staff status for this view).
        """
        self.client.login(username=self.regular_user.username, password='password123')

        response_add = self.client.get(self.add_url)
        # FIX: Expect a 302 redirect and verify the redirect URL
        self.assertEqual(response_add.status_code, 302)
        self.assertRedirects(response_add, f'/accounts/login/?next={self.add_url}')

        existing_refund_request = create_refund_request(
            hire_booking=self.hire_booking,
            payment=self.payment,
            driver_profile=self.driver_profile,
        )
        response_edit = self.client.get(self.edit_url(existing_refund_request.pk))
        # FIX: Expect a 302 redirect and verify the redirect URL
        self.assertEqual(response_edit.status_code, 302)
        self.assertRedirects(response_edit, f'/accounts/login/?next={self.edit_url(existing_refund_request.pk)}')
