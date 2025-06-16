# payments/tests/form_tests/test_admin_hire_refund_request_form.py

from django.test import TestCase
from decimal import Decimal
from payments.forms.admin_refund_request_form import AdminRefundRequestForm
from payments.models.RefundRequest import RefundRequest
from payments.models.PaymentModel import Payment
from hire.models import HireBooking
from django.utils import timezone

# Updated imports to use the factory classes directly from payments.tests.test_helpers.model_factories
from payments.tests.test_helpers.model_factories import (
    PaymentFactory, HireBookingFactory, UserFactory, DriverProfileFactory,
    SalesBookingFactory, SalesProfileFactory, MotorcycleFactory,
    ServiceBookingFactory, ServiceProfileFactory, CustomerMotorcycleFactory, ServiceTypeFactory
)


class AdminRefundRequestFormTests(TestCase):
    """
    Tests for the AdminRefundRequestForm.
    """

    def setUp(self):
        """Set up test data for all tests."""
        self.admin_user = UserFactory(username='admin', email='admin@example.com', is_staff=True)
        self.driver_profile = DriverProfileFactory(email='test@example.com')
        self.sales_profile = SalesProfileFactory(user=self.admin_user)
        self.service_profile = ServiceProfileFactory(user=self.admin_user)
        self.motorcycle_gen = MotorcycleFactory() # Generic motorcycle for hire/sales

        # Hire Booking Setup
        self.payment_succeeded_hire = PaymentFactory(
            amount=Decimal('500.00'),
            status='succeeded',
            driver_profile=self.driver_profile,
            stripe_payment_intent_id='pi_test_succeeded_hire'
        )
        self.hire_booking_paid = HireBookingFactory(
            driver_profile=self.driver_profile,
            payment=self.payment_succeeded_hire,
            motorcycle=self.motorcycle_gen, # Link motorcycle
            amount_paid=self.payment_succeeded_hire.amount,
            grand_total=self.payment_succeeded_hire.amount,
            payment_status='paid',
            status='confirmed',
            pickup_date=timezone.now().date() + timezone.timedelta(days=10),
            return_date=timezone.now().date() + timezone.timedelta(days=12),
        )
        self.payment_succeeded_hire.hire_booking = self.hire_booking_paid
        self.payment_succeeded_hire.save()

        self.payment_deposit_paid_hire = PaymentFactory(
            amount=Decimal('100.00'),
            status='succeeded',
            driver_profile=self.driver_profile,
            stripe_payment_intent_id='pi_test_deposit_hire'
        )
        self.hire_booking_deposit = HireBookingFactory(
            driver_profile=self.driver_profile,
            payment=self.payment_deposit_paid_hire,
            motorcycle=self.motorcycle_gen, # Link motorcycle
            amount_paid=self.payment_deposit_paid_hire.amount,
            grand_total=Decimal('500.00'), 
            deposit_amount=self.payment_deposit_paid_hire.amount,
            payment_status='deposit_paid',
            status='confirmed',
            pickup_date=timezone.now().date() + timezone.timedelta(days=5),
            return_date=timezone.now().date() + timezone.timedelta(days=7),
        )
        self.payment_deposit_paid_hire.hire_booking = self.hire_booking_deposit
        self.payment_deposit_paid_hire.save()

        self.hire_booking_unpaid = HireBookingFactory(
            driver_profile=self.driver_profile,
            payment=None, 
            motorcycle=self.motorcycle_gen, # Link motorcycle
            amount_paid=Decimal('0.00'),
            grand_total=Decimal('300.00'),
            payment_status='unpaid',
            status='pending',
            pickup_date=timezone.now().date() + timezone.timedelta(days=20),
            return_date=timezone.now().date() + timezone.timedelta(days=22),
        )

        # Service Booking Setup
        self.motorcycle_service = CustomerMotorcycleFactory(service_profile=self.service_profile)
        self.service_type_obj = ServiceTypeFactory()
        self.payment_succeeded_service = PaymentFactory(
            amount=Decimal('250.00'),
            status='succeeded',
            service_customer_profile=self.service_profile,
            stripe_payment_intent_id='pi_test_succeeded_service'
        )
        self.service_booking_paid = ServiceBookingFactory(
            service_profile=self.service_profile,
            customer_motorcycle=self.motorcycle_service,
            service_type=self.service_type_obj,
            payment=self.payment_succeeded_service,
            amount_paid=self.payment_succeeded_service.amount,
            calculated_total=self.payment_succeeded_service.amount,
            payment_status='paid',
            booking_status='confirmed',
        )
        self.payment_succeeded_service.service_booking = self.service_booking_paid
        self.payment_succeeded_service.save()

        # Sales Booking Setup
        self.motorcycle_sales = MotorcycleFactory() # Use general MotorcycleFactory
        self.payment_deposit_sales = PaymentFactory(
            amount=Decimal('100.00'),
            status='succeeded',
            sales_customer_profile=self.sales_profile,
            stripe_payment_intent_id='pi_test_deposit_sales'
        )
        self.sales_booking_deposit = SalesBookingFactory(
            sales_profile=self.sales_profile,
            motorcycle=self.motorcycle_sales,
            payment=self.payment_deposit_sales,
            amount_paid=self.payment_deposit_sales.amount,
            payment_status='deposit_paid',
            booking_status='deposit_paid',
        )
        self.payment_deposit_sales.sales_booking = self.sales_booking_deposit
        self.payment_deposit_sales.save()


    def test_form_valid_data_create_hire(self):
        """
        Test that the form is valid with correct data for creating a new request for a hire booking.
        """
        form_data = {
            'hire_booking': self.hire_booking_paid.pk,
            'reason': 'Customer requested full refund.',
            'staff_notes': 'Processed as per policy.',
            'amount_to_refund': '500.00',
        }
        form = AdminRefundRequestForm(data=form_data)
        self.assertTrue(form.is_valid(), f"Form is not valid: {form.errors}")

        refund_request = form.save()
        self.assertIsInstance(refund_request, RefundRequest)
        self.assertEqual(refund_request.hire_booking, self.hire_booking_paid)
        self.assertEqual(refund_request.payment, self.payment_succeeded_hire)
        self.assertEqual(refund_request.driver_profile, self.driver_profile)
        self.assertEqual(refund_request.reason, 'Customer requested full refund.')
        self.assertEqual(refund_request.staff_notes, 'Processed as per policy.')
        self.assertEqual(refund_request.amount_to_refund, Decimal('500.00'))
        self.assertIsNotNone(refund_request.requested_at)
        self.assertEqual(RefundRequest.objects.count(), 1)

    def test_form_valid_data_create_service(self):
        """
        Test that the form is valid with correct data for creating a new request for a service booking.
        """
        form_data = {
            'service_booking': self.service_booking_paid.pk,
            'reason': 'Customer requested service refund.',
            'staff_notes': 'Service refund processed.',
            'amount_to_refund': '250.00',
        }
        form = AdminRefundRequestForm(data=form_data)
        self.assertTrue(form.is_valid(), f"Form is not valid: {form.errors}")

        refund_request = form.save()
        self.assertIsInstance(refund_request, RefundRequest)
        self.assertEqual(refund_request.service_booking, self.service_booking_paid)
        self.assertEqual(refund_request.payment, self.payment_succeeded_service)
        self.assertEqual(refund_request.service_profile, self.service_profile)
        self.assertEqual(refund_request.reason, 'Customer requested service refund.')
        self.assertEqual(refund_request.staff_notes, 'Service refund processed.')
        self.assertEqual(refund_request.amount_to_refund, Decimal('250.00'))
        self.assertIsNotNone(refund_request.requested_at)
        self.assertEqual(RefundRequest.objects.count(), 1)

    def test_form_valid_data_create_sales(self):
        """
        Test that the form is valid with correct data for creating a new request for a sales booking.
        """
        form_data = {
            'sales_booking': self.sales_booking_deposit.pk,
            'reason': 'Customer cancelled sale.',
            'staff_notes': 'Sales deposit refund initiated.',
            'amount_to_refund': '100.00',
        }
        form = AdminRefundRequestForm(data=form_data)
        self.assertTrue(form.is_valid(), f"Form is not valid: {form.errors}")

        refund_request = form.save()
        self.assertIsInstance(refund_request, RefundRequest)
        self.assertEqual(refund_request.sales_booking, self.sales_booking_deposit)
        self.assertEqual(refund_request.payment, self.payment_deposit_sales)
        self.assertEqual(refund_request.sales_profile, self.sales_profile)
        self.assertEqual(refund_request.reason, 'Customer cancelled sale.')
        self.assertEqual(refund_request.staff_notes, 'Sales deposit refund initiated.')
        self.assertEqual(refund_request.amount_to_refund, Decimal('100.00'))
        self.assertIsNotNone(refund_request.requested_at)
        self.assertEqual(RefundRequest.objects.count(), 1)


    def test_form_valid_data_deposit_paid(self):
        """
        Test that the form is valid for a deposit-paid hire booking.
        """
        form_data = {
            'hire_booking': self.hire_booking_deposit.pk,
            'reason': 'Customer requested deposit refund.',
            'staff_notes': 'Deposit refund initiated.',
            'amount_to_refund': '100.00',
        }
        form = AdminRefundRequestForm(data=form_data)
        self.assertTrue(form.is_valid(), f"Form is not valid: {form.errors}")

        refund_request = form.save()
        self.assertIsInstance(refund_request, RefundRequest)
        self.assertEqual(refund_request.hire_booking, self.hire_booking_deposit)
        self.assertEqual(refund_request.payment, self.payment_deposit_paid_hire)
        self.assertEqual(refund_request.driver_profile, self.driver_profile)
        self.assertEqual(refund_request.amount_to_refund, Decimal('100.00'))

    def test_form_invalid_no_booking_selected(self):
        """
        Test that the form is invalid if no booking (hire, service, or sales) is provided.
        Updated error message to reflect all booking types.
        """
        form_data = {
            'reason': 'Test reason',
            'staff_notes': 'Test notes',
            'amount_to_refund': '100.00',
        }
        form = AdminRefundRequestForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('__all__', form.errors)
        self.assertEqual(form.errors['__all__'], ['Please select a Hire, Service, or Sales Booking.'])

    def test_form_invalid_multiple_bookings_selected(self):
        """
        Test that the form is invalid if multiple booking types are selected.
        """
        form_data = {
            'hire_booking': self.hire_booking_paid.pk,
            'service_booking': self.service_booking_paid.pk, # Select both hire and service
            'reason': 'Test reason',
            'staff_notes': 'Test notes',
            'amount_to_refund': '100.00',
        }
        form = AdminRefundRequestForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('__all__', form.errors)
        self.assertEqual(form.errors['__all__'], ['Please select only one type of booking (Hire, Service, or Sales).'])

        form_data_2 = {
            'hire_booking': self.hire_booking_paid.pk,
            'sales_booking': self.sales_booking_deposit.pk, # Select both hire and sales
            'reason': 'Test reason',
            'staff_notes': 'Test notes',
            'amount_to_refund': '100.00',
        }
        form_2 = AdminRefundRequestForm(data=form_data_2)
        self.assertFalse(form_2.is_valid())
        self.assertIn('__all__', form_2.errors)
        self.assertEqual(form_2.errors['__all__'], ['Please select only one type of booking (Hire, Service, or Sales).'])


    def test_form_invalid_amount_exceeds_paid(self):
        """
        Test that the form is invalid if amount_to_refund exceeds amount_paid for any booking type.
        """
        # Hire Booking
        form_data_hire = { # Renamed to avoid UnboundLocalError
            'hire_booking': self.hire_booking_paid.pk,
            'reason': 'Customer requested too much.',
            'staff_notes': 'Amount too high.',
            'amount_to_refund': '500.01', # Exceeds paid amount
        }
        form_hire = AdminRefundRequestForm(data=form_data_hire)
        self.assertFalse(form_hire.is_valid())
        self.assertIn('amount_to_refund', form_hire.errors)
        self.assertIn("cannot exceed the amount paid", form_hire.errors['amount_to_refund'][0])

        # Service Booking
        form_data_service = { # Renamed to avoid UnboundLocalError
            'service_booking': self.service_booking_paid.pk,
            'reason': 'Customer requested too much.',
            'staff_notes': 'Amount too high.',
            'amount_to_refund': '250.01', # Exceeds paid amount
        }
        form_service = AdminRefundRequestForm(data=form_data_service)
        self.assertFalse(form_service.is_valid())
        self.assertIn('amount_to_refund', form_service.errors)
        self.assertIn("cannot exceed the amount paid", form_service.errors['amount_to_refund'][0])

        # Sales Booking
        form_data_sales = { # Renamed to avoid UnboundLocalError
            'sales_booking': self.sales_booking_deposit.pk,
            'reason': 'Customer requested too much.',
            'staff_notes': 'Amount too high.',
            'amount_to_refund': '100.01', # Exceeds paid amount
        }
        form_sales = AdminRefundRequestForm(data=form_data_sales)
        self.assertFalse(form_sales.is_valid())
        self.assertIn('amount_to_refund', form_sales.errors)
        self.assertIn("cannot exceed the amount paid", form_sales.errors['amount_to_refund'][0])


    def test_form_invalid_booking_without_payment(self):
        """
        Test that the form is invalid if the selected booking is not in the queryset (e.g., unpaid).
        """
        form_data = {
            'hire_booking': self.hire_booking_unpaid.pk, # This booking is not in the queryset
            'reason': 'Booking not paid.',
            'staff_notes': 'No payment.',
            'amount_to_refund': '10.00',
        }
        form = AdminRefundRequestForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('hire_booking', form.errors)
        self.assertIn("Select a valid choice. That choice is not one of the available choices.", form.errors['hire_booking'])


    def test_form_initial_values_for_new_instance(self):
        """
        Test that initial values like is_admin_initiated and status are NOT set by the form itself.
        These are now handled by the view.
        """
        form = AdminRefundRequestForm()
        self.assertIsNone(form.initial.get('is_admin_initiated'))
        self.assertIsNone(form.initial.get('status'))

    def test_form_edit_instance(self):
        """
        Test that the form correctly loads and saves an existing instance for a hire booking.
        """
        existing_refund_request = RefundRequest.objects.create(
            hire_booking=self.hire_booking_paid,
            payment=self.payment_succeeded_hire,
            driver_profile=self.driver_profile,
            reason='Original reason',
            staff_notes='Original notes',
            amount_to_refund=Decimal('250.00'),
            is_admin_initiated=True,
            status='pending',
        )

        form_data = {
            'hire_booking': self.hire_booking_paid.pk, 
            'reason': 'Updated reason',
            'staff_notes': 'Updated notes.',
            'amount_to_refund': '300.00',
        }
        form = AdminRefundRequestForm(data=form_data, instance=existing_refund_request)
        self.assertTrue(form.is_valid(), f"Form is not valid: {form.errors}")

        updated_refund_request = form.save()
        self.assertEqual(updated_refund_request.pk, existing_refund_request.pk)
        self.assertEqual(updated_refund_request.reason, 'Updated reason')
        self.assertEqual(updated_refund_request.staff_notes, 'Updated notes.')
        self.assertEqual(updated_refund_request.amount_to_refund, Decimal('300.00'))
        self.assertEqual(updated_refund_request.status, 'pending')
        self.assertTrue(updated_refund_request.is_admin_initiated)
        self.assertEqual(RefundRequest.objects.count(), 1) 

    def test_form_edit_instance_service_booking(self):
        """
        Test that the form correctly loads and saves an existing instance for a service booking.
        """
        existing_refund_request = RefundRequest.objects.create(
            service_booking=self.service_booking_paid,
            payment=self.payment_succeeded_service,
            service_profile=self.service_profile,
            reason='Original service reason',
            staff_notes='Original service notes',
            amount_to_refund=Decimal('150.00'),
            is_admin_initiated=True,
            status='pending',
        )

        form_data = {
            'service_booking': self.service_booking_paid.pk, 
            'reason': 'Updated service reason',
            'staff_notes': 'Updated service notes.',
            'amount_to_refund': '200.00',
        }
        form = AdminRefundRequestForm(data=form_data, instance=existing_refund_request)
        self.assertTrue(form.is_valid(), f"Form is not valid: {form.errors}")

        updated_refund_request = form.save()
        self.assertEqual(updated_refund_request.pk, existing_refund_request.pk)
        self.assertEqual(updated_refund_request.reason, 'Updated service reason')
        self.assertEqual(updated_refund_request.staff_notes, 'Updated service notes.')
        self.assertEqual(updated_refund_request.amount_to_refund, Decimal('200.00'))
        self.assertEqual(updated_refund_request.status, 'pending')
        self.assertTrue(updated_refund_request.is_admin_initiated)
        self.assertEqual(RefundRequest.objects.count(), 1)


    def test_form_edit_instance_sales_booking(self):
        """
        Test that the form correctly loads and saves an existing instance for a sales booking.
        """
        existing_refund_request = RefundRequest.objects.create(
            sales_booking=self.sales_booking_deposit,
            payment=self.payment_deposit_sales,
            sales_profile=self.sales_profile,
            reason='Original sales reason',
            staff_notes='Original sales notes',
            amount_to_refund=Decimal('50.00'),
            is_admin_initiated=True,
            status='pending',
        )

        form_data = {
            'sales_booking': self.sales_booking_deposit.pk, 
            'reason': 'Updated sales reason',
            'staff_notes': 'Updated sales notes.',
            'amount_to_refund': '75.00',
        }
        form = AdminRefundRequestForm(data=form_data, instance=existing_refund_request)
        self.assertTrue(form.is_valid(), f"Form is not valid: {form.errors}")

        updated_refund_request = form.save()
        self.assertEqual(updated_refund_request.pk, existing_refund_request.pk)
        self.assertEqual(updated_refund_request.reason, 'Updated sales reason')
        self.assertEqual(updated_refund_request.staff_notes, 'Updated sales notes.')
        self.assertEqual(updated_refund_request.amount_to_refund, Decimal('75.00'))
        self.assertEqual(updated_refund_request.status, 'pending')
        self.assertTrue(updated_refund_request.is_admin_initiated)
        self.assertEqual(RefundRequest.objects.count(), 1)


    def test_form_optional_fields_blank(self):
        """
        Test that the form is valid when optional fields are left blank.
        """
        form_data = {
            'hire_booking': self.hire_booking_paid.pk,
            'reason': '', 
            'staff_notes': '', 
            'amount_to_refund': 50,
        }
        form = AdminRefundRequestForm(data=form_data)
        self.assertTrue(form.is_valid(), f"Form is not valid: {form.errors}")
        refund_request = form.save()
        self.assertEqual(refund_request.reason, '')
        self.assertEqual(refund_request.staff_notes, '')

