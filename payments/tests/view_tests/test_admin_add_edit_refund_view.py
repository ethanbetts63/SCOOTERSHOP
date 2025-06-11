
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib import messages
from django.utils import timezone
from decimal import Decimal
from unittest.mock import patch
from payments.tests.test_helpers.model_factories import (
    RefundRequestFactory, HireBookingFactory, ServiceBookingFactory,
    PaymentFactory, UserFactory
)
from payments.models import RefundRequest
ADMIN_REFUND_MANAGEMENT_URL = reverse('payments:admin_refund_management')

LOGIN_URL = reverse('users:login') 

class AdminAddEditRefundRequestViewTests(TestCase):
    """
    Tests for the AdminAddEditRefundRequestView.
    This view handles both creation and editing of RefundRequest instances
    for both HireBookings and ServiceBookings.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up non-modified data for all test methods.
        Create an admin user and a regular user.
        """
        cls.client = Client()
        cls.admin_user = UserFactory(is_staff=True, is_superuser=True)
        cls.regular_user = UserFactory(is_staff=False, is_superuser=False)

        # Create some common objects for testing
        cls.hire_booking_paid = HireBookingFactory(
            payment_status='paid',
            amount_paid=Decimal('500.00'),
            payment=PaymentFactory(amount=Decimal('500.00')) # Ensure payment has correct amount
        )
        cls.service_booking_deposit = ServiceBookingFactory(
            payment_status='deposit_paid',
            amount_paid=Decimal('100.00'),
            payment=PaymentFactory(amount=Decimal('100.00')) # Ensure payment has correct amount
        )

    def setUp(self):
        """
        Set up data for each test method.
        Ensure admin user is logged in by default for most tests.
        """
        self.client.force_login(self.admin_user)
        # Patch the `is_admin` utility to always return True for admin_user
        # and False for others during these tests to control access.
        self.patcher = patch('users.views.auth.is_admin')
        self.mock_is_admin = self.patcher.start()
        self.mock_is_admin.return_value = True

    def tearDown(self):
        """
        Clean up after each test method.
        Stop the patcher.
        """
        self.patcher.stop()

    # --- GET Request Tests ---

    def test_get_create_new_refund_request_form_as_admin(self):
        """
        Tests that an admin can access the form for creating a new refund request.
        """
        response = self.client.get(reverse('payments:add_refund_request'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'payments/admin_refund_form.html')
        self.assertIn('form', response.context)
        self.assertIn('Create New Refund Request', response.context['title'])
        self.assertIsNone(response.context['refund_request'])
        self.assertEqual(response.context['booking_reference'], "N/A")

    def test_get_edit_hire_refund_request_form_as_admin(self):
        """
        Tests that an admin can access and pre-populated form for editing an existing
        hire booking refund request.
        """
        refund_request = RefundRequestFactory(hire_booking=self.hire_booking_paid, service_booking=None)
        response = self.client.get(reverse('payments:edit_refund_request', args=[refund_request.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'payments/admin_refund_form.html')
        self.assertIn('form', response.context)
        self.assertEqual(response.context['form'].instance, refund_request)
        self.assertIn(f"Edit Hire Refund Request for Booking {self.hire_booking_paid.booking_reference}", response.context['title'])
        self.assertEqual(response.context['refund_request'], refund_request)
        self.assertEqual(response.context['booking_reference'], self.hire_booking_paid.booking_reference)
        # Check initial form values for hire_booking - CORRECTED ASSERTION
        self.assertEqual(response.context['form'].initial['hire_booking'].pk, self.hire_booking_paid.pk)
        self.assertIsNone(response.context['form'].initial.get('service_booking'))


    def test_get_edit_service_refund_request_form_as_admin(self):
        """
        Tests that an admin can access and pre-populated form for editing an existing
        service booking refund request.
        """
        refund_request = RefundRequestFactory(service_booking=self.service_booking_deposit, hire_booking=None)
        response = self.client.get(reverse('payments:edit_refund_request', args=[refund_request.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'payments/admin_refund_form.html')
        self.assertIn('form', response.context)
        self.assertEqual(response.context['form'].instance, refund_request)
        self.assertIn(f"Edit Service Refund Request for Booking {self.service_booking_deposit.service_booking_reference}", response.context['title'])
        self.assertEqual(response.context['refund_request'], refund_request)
        self.assertEqual(response.context['booking_reference'], self.service_booking_deposit.service_booking_reference)
        # Check initial form values for service_booking - CORRECTED ASSERTION
        self.assertEqual(response.context['form'].initial['service_booking'].pk, self.service_booking_deposit.pk)
        self.assertIsNone(response.context['form'].initial.get('hire_booking'))

    def test_get_not_admin_redirects(self):
        """
        Tests that a non-admin user is redirected from the admin refund request view
        to the custom login page.
        """
        self.client.force_login(self.regular_user)
        self.mock_is_admin.return_value = False # Ensure is_admin returns False for this user
        response = self.client.get(reverse('payments:add_refund_request'))
        self.assertEqual(response.status_code, 302)
        # Redirects to your custom login view, using 'add_refund_request'
        self.assertRedirects(response, f"{LOGIN_URL}?next={reverse('payments:add_refund_request')}")


    # --- POST Request Tests ---

    def test_post_create_hire_refund_request_success(self):
        """
        Tests successful creation of a new refund request for a hire booking by admin.
        """
        initial_refund_count = RefundRequest.objects.count()
        data = {
            'hire_booking': self.hire_booking_paid.pk,
            'service_booking': '', # Ensure service_booking is empty
            'reason': 'Customer changed mind',
            'staff_notes': 'Refund processed by admin.',
            'amount_to_refund': '500.00',
        }
        response = self.client.post(reverse('payments:add_refund_request'), data)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, ADMIN_REFUND_MANAGEMENT_URL)
        self.assertEqual(RefundRequest.objects.count(), initial_refund_count + 1)

        new_refund_request = RefundRequest.objects.latest('pk') # Get the latest created request
        self.assertEqual(new_refund_request.hire_booking, self.hire_booking_paid)
        self.assertIsNone(new_refund_request.service_booking) # Should be None
        self.assertEqual(new_refund_request.reason, 'Customer changed mind')
        self.assertEqual(new_refund_request.staff_notes, 'Refund processed by admin.')
        self.assertEqual(new_refund_request.amount_to_refund, Decimal('500.00'))
        self.assertTrue(new_refund_request.is_admin_initiated)
        self.assertEqual(new_refund_request.status, 'reviewed_pending_approval') # New requests by admin should go to this status
        # CORRECTED ASSERTION: processed_by and processed_at should be None for this status
        self.assertIsNone(new_refund_request.processed_by)
        self.assertIsNone(new_refund_request.processed_at)

        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 1)
        self.assertIn("Refund Request for booking", str(messages_list[0]))
        self.assertIn("saved successfully!", str(messages_list[0]))
        self.assertEqual(messages_list[0].tags, 'success')


    def test_post_create_service_refund_request_success(self):
        """
        Tests successful creation of a new refund request for a service booking by admin.
        """
        initial_refund_count = RefundRequest.objects.count()
        data = {
            'hire_booking': '', # Ensure hire_booking is empty
            'service_booking': self.service_booking_deposit.pk,
            'reason': 'Service issue, full refund.',
            'staff_notes': 'Refund for poor service experience.',
            'amount_to_refund': '100.00',
        }
        response = self.client.post(reverse('payments:add_refund_request'), data)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, ADMIN_REFUND_MANAGEMENT_URL)
        self.assertEqual(RefundRequest.objects.count(), initial_refund_count + 1)

        new_refund_request = RefundRequest.objects.latest('pk')
        self.assertIsNone(new_refund_request.hire_booking) # Should be None
        self.assertEqual(new_refund_request.service_booking, self.service_booking_deposit)
        self.assertEqual(new_refund_request.reason, 'Service issue, full refund.')
        self.assertEqual(new_refund_request.staff_notes, 'Refund for poor service experience.')
        self.assertEqual(new_refund_request.amount_to_refund, Decimal('100.00'))
        self.assertTrue(new_refund_request.is_admin_initiated)
        self.assertEqual(new_refund_request.status, 'reviewed_pending_approval')
        # CORRECTED ASSERTION: processed_by and processed_at should be None for this status
        self.assertIsNone(new_refund_request.processed_by)
        self.assertIsNone(new_refund_request.processed_at)

        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 1)
        self.assertIn("Refund Request for booking", str(messages_list[0]))
        self.assertIn("saved successfully!", str(messages_list[0]))
        self.assertEqual(messages_list[0].tags, 'success')

    def test_post_edit_hire_refund_request_success(self):
        """
        Tests successful editing of an existing hire refund request.
        Changes status, amount, and notes.
        """
        refund_request = RefundRequestFactory(
            hire_booking=self.hire_booking_paid,
            status='pending', # Start as pending
            amount_to_refund=Decimal('0.00'),
            staff_notes='',
            is_admin_initiated=False,
            processed_by=None,
            processed_at=None
        )
        data = {
            'hire_booking': self.hire_booking_paid.pk,
            'service_booking': '',
            'reason': refund_request.reason, # Keep existing reason
            'staff_notes': 'Updated staff notes, request approved.',
            'amount_to_refund': '450.00', # Partial refund
        }
        response = self.client.post(reverse('payments:edit_refund_request', args=[refund_request.pk]), data)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, ADMIN_REFUND_MANAGEMENT_URL)

        refund_request.refresh_from_db()
        self.assertEqual(refund_request.amount_to_refund, Decimal('450.00'))
        self.assertEqual(refund_request.staff_notes, 'Updated staff notes, request approved.')
        self.assertTrue(refund_request.is_admin_initiated) # Should be set to True if admin modifies
        self.assertEqual(refund_request.status, 'reviewed_pending_approval') # Should transition to this if was 'pending'
        # CORRECTED ASSERTION: processed_by and processed_at should be None for this status
        self.assertIsNone(refund_request.processed_by)
        self.assertIsNone(refund_request.processed_at)

        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 1)
        self.assertIn("Refund Request for booking", str(messages_list[0]))
        self.assertIn("saved successfully!", str(messages_list[0]))
        self.assertEqual(messages_list[0].tags, 'success')


    def test_post_edit_service_refund_request_success(self):
        """
        Tests successful editing of an existing service refund request.
        """
        refund_request = RefundRequestFactory(
            service_booking=self.service_booking_deposit,
            status='pending', # CORRECTED: Changed from 'unverified' to 'pending' to trigger status change in view
            amount_to_refund=Decimal('0.00'),
            staff_notes='',
            is_admin_initiated=False,
            processed_by=None,
            processed_at=None
        )
        data = {
            'hire_booking': '',
            'service_booking': self.service_booking_deposit.pk,
            'reason': refund_request.reason,
            'staff_notes': 'Admin reviewed and approved, full refund.',
            'amount_to_refund': '100.00',
        }
        response = self.client.post(reverse('payments:edit_refund_request', args=[refund_request.pk]), data)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, ADMIN_REFUND_MANAGEMENT_URL)

        refund_request.refresh_from_db()
        self.assertEqual(refund_request.amount_to_refund, Decimal('100.00'))
        self.assertEqual(refund_request.staff_notes, 'Admin reviewed and approved, full refund.')
        self.assertTrue(refund_request.is_admin_initiated)
        self.assertEqual(refund_request.status, 'reviewed_pending_approval')
        # CORRECTED ASSERTION: processed_by and processed_at should be None for this status
        self.assertIsNone(refund_request.processed_by)
        self.assertIsNone(refund_request.processed_at)


        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 1)
        self.assertIn("Refund Request for booking", str(messages_list[0]))
        self.assertIn("saved successfully!", str(messages_list[0]))
        self.assertEqual(messages_list[0].tags, 'success')

    def test_post_form_invalid(self):
        """
        Tests form submission with invalid data (e.g., amount to refund too high).
        """
        hire_booking = HireBookingFactory(
            payment_status='paid',
            amount_paid=Decimal('200.00'),
            payment=PaymentFactory(amount=Decimal('200.00'))
        )
        refund_request = RefundRequestFactory(hire_booking=hire_booking, status='pending')

        data = {
            'hire_booking': hire_booking.pk,
            'service_booking': '',
            'reason': 'Test Reason',
            'staff_notes': 'Test Notes',
            'amount_to_refund': '2000.00', # Invalid amount, much higher than payment.amount
        }
        response = self.client.post(reverse('payments:edit_refund_request', args=[refund_request.pk]), data)

        self.assertEqual(response.status_code, 200) # Should re-render the form
        self.assertTemplateUsed(response, 'payments/admin_refund_form.html')
        self.assertIn('form', response.context)
        self.assertTrue(response.context['form'].errors)
        self.assertIn('amount_to_refund', response.context['form'].errors)

        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 1)
        self.assertIn("Please correct the errors below.", str(messages_list[0]))
        self.assertEqual(messages_list[0].tags, 'error')

        refund_request.refresh_from_db()
        self.assertEqual(refund_request.status, 'pending') # Status should not change on invalid form
        self.assertIsNone(refund_request.processed_by) # Should not be set
        self.assertIsNone(refund_request.processed_at) # Should not be set


    def test_post_amount_exceeds_paid_amount_validation(self):
        """
        Tests that the form correctly validates if `amount_to_refund` exceeds `payment.amount`.
        """
        hire_booking = HireBookingFactory(
            payment_status='paid',
            amount_paid=Decimal('200.00'),
            payment=PaymentFactory(amount=Decimal('200.00'))
        )
        data = {
            'hire_booking': hire_booking.pk,
            'service_booking': '',
            'reason': 'Test Reason',
            'staff_notes': 'Test Notes',
            'amount_to_refund': '200.01', # Just slightly over
        }
        response = self.client.post(reverse('payments:add_refund_request'), data)

        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        self.assertIn('amount_to_refund', form.errors)
        self.assertIn(f"Amount to refund (${data['amount_to_refund']}) cannot exceed the amount paid for this booking (${hire_booking.payment.amount}).",
                      form.errors['amount_to_refund'])

    def test_post_negative_amount_to_refund_validation(self):
        """
        Tests that the form correctly validates if `amount_to_refund` is negative.
        """
        hire_booking = HireBookingFactory(
            payment_status='paid',
            amount_paid=Decimal('200.00'),
            payment=PaymentFactory(amount=Decimal('200.00'))
        )
        data = {
            'hire_booking': hire_booking.pk,
            'service_booking': '',
            'reason': 'Test Reason',
            'staff_notes': 'Test Notes',
            'amount_to_refund': '-10.00', # Negative amount
        }
        response = self.client.post(reverse('payments:add_refund_request'), data)

        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        self.assertIn('amount_to_refund', form.errors)
        self.assertIn("Amount to refund cannot be a negative value.", form.errors['amount_to_refund'])

    def test_post_select_both_bookings_error(self):
        """
        Tests validation error when both hire_booking and service_booking are selected.
        """
        data = {
            'hire_booking': self.hire_booking_paid.pk,
            'service_booking': self.service_booking_deposit.pk,
            'reason': 'Test Reason',
            'staff_notes': 'Test Notes',
            'amount_to_refund': '50.00',
        }
        response = self.client.post(reverse('payments:add_refund_request'), data)

        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        # CORRECTED: Use form.non_field_errors()
        self.assertIn("Please select either a Hire Booking or a Service Booking, not both.",
                      form.non_field_errors())

    def test_post_no_booking_selected_error(self):
        """
        Tests validation error when neither hire_booking nor service_booking are selected.
        """
        data = {
            'hire_booking': '',
            'service_booking': '',
            'reason': 'Test Reason',
            'staff_notes': 'Test Notes',
            'amount_to_refund': '50.00',
        }
        response = self.client.post(reverse('payments:add_refund_request'), data)

        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        # CORRECTED: Use form.non_field_errors()
        self.assertIn("Please select either a Hire Booking or a Service Booking.",
                      form.non_field_errors())

    def test_post_status_transition_to_reviewed_pending_approval(self):
        """
        Tests that an existing 'pending' refund request status transitions to
        'reviewed_pending_approval' when an admin edits it.
        """
        refund_request = RefundRequestFactory(
            hire_booking=self.hire_booking_paid,
            status='pending', # User submitted, now admin reviews
            is_admin_initiated=False, # Should be False initially for user-submitted
            processed_by=None,
            processed_at=None
        )
        data = {
            'hire_booking': self.hire_booking_paid.pk,
            'service_booking': '',
            'reason': refund_request.reason,
            'staff_notes': 'Admin is now reviewing this previously user-submitted request.',
            'amount_to_refund': '250.00',
        }
        response = self.client.post(reverse('payments:edit_refund_request', args=[refund_request.pk]), data)
        self.assertEqual(response.status_code, 302)
        refund_request.refresh_from_db()
        self.assertEqual(refund_request.status, 'reviewed_pending_approval')
        # CORRECTED ASSERTION: processed_by and processed_at should be None for this status
        self.assertIsNone(refund_request.processed_by)
        self.assertIsNone(refund_request.processed_at)


    def test_post_status_already_approved_no_change_to_processed_by(self):
        """
        Tests that if a refund request is already in an approved/refunded status,
        and `processed_by` is already set, it's not overwritten when edited.
        """
        original_processor = UserFactory() # A different user, simulating prior processing
        original_processed_at = timezone.now() - timezone.timedelta(days=1)

        refund_request = RefundRequestFactory(
            hire_booking=self.hire_booking_paid,
            status='approved', # Already approved
            processed_by=original_processor,
            processed_at=original_processed_at,
            amount_to_refund=Decimal('500.00')
        )
        data = {
            'hire_booking': self.hire_booking_paid.pk,
            'service_booking': '',
            'reason': refund_request.reason,
            'staff_notes': 'Just adding more notes, no status change.',
            'amount_to_refund': '500.00', # Keep same amount
        }
        response = self.client.post(reverse('payments:edit_refund_request', args=[refund_request.pk]), data)
        self.assertEqual(response.status_code, 302)
        refund_request.refresh_from_db()
        self.assertEqual(refund_request.status, 'approved') # Status remains
        self.assertEqual(refund_request.processed_by, original_processor) # Should NOT change
        self.assertEqual(refund_request.processed_at.date(), original_processed_at.date()) # Date part should match


    def test_post_no_admin_redirects(self):
        """
        Tests that a non-admin user is redirected on POST attempts
        to the custom login page.
        """
        self.client.force_login(self.regular_user)
        self.mock_is_admin.return_value = False # Ensure is_admin returns False for this user

        data = {
            'hire_booking': self.hire_booking_paid.pk,
            'service_booking': '',
            'reason': 'Attempt by non-admin',
            'staff_notes': 'Unauthorized access',
            'amount_to_refund': '10.00',
        }
        response = self.client.post(reverse('payments:add_refund_request'), data)
        self.assertEqual(response.status_code, 302)
        # Redirects to your custom login view, using 'add_refund_request'
        self.assertRedirects(response, f"{LOGIN_URL}?next={reverse('payments:add_refund_request')}")
        self.assertEqual(RefundRequest.objects.count(), 0) # No refund request should be created
