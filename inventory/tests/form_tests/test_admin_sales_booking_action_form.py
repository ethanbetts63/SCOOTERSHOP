
from django.test import TestCase
from inventory.forms import SalesBookingActionForm
from inventory.tests.test_helpers.model_factories import SalesBookingFactory, PaymentFactory
from decimal import Decimal

class SalesBookingActionFormTest(TestCase):

    def setUp(self):
        self.sales_booking = SalesBookingFactory(payment=PaymentFactory(amount=Decimal('100.00')))
        self.sales_booking_no_payment = SalesBookingFactory(payment=None)
        self.sales_booking_zero_payment = SalesBookingFactory(payment=PaymentFactory(amount=Decimal('0.00')))

    def test_valid_confirm_action_form(self):
        form = SalesBookingActionForm(data={
            'sales_booking_id': self.sales_booking.pk,
            'action': 'confirm',
            'message': 'Booking confirmed successfully.',
            'send_notification': True,
        })
        self.assertTrue(form.is_valid(), form.errors)

    def test_valid_reject_action_form_no_refund(self):
        form = SalesBookingActionForm(data={
            'sales_booking_id': self.sales_booking.pk,
            'action': 'reject',
            'message': 'Booking rejected.',
            'send_notification': False,
            'initiate_refund': False,
        })
        self.assertTrue(form.is_valid(), form.errors)

    def test_valid_reject_action_form_with_refund(self):
        form = SalesBookingActionForm(data={
            'sales_booking_id': self.sales_booking.pk,
            'action': 'reject',
            'message': 'Booking rejected, refund initiated.',
            'send_notification': True,
            'initiate_refund': True,
            'refund_amount': Decimal('50.00'),
        })
        self.assertTrue(form.is_valid(), form.errors)

    def test_reject_action_missing_refund_amount_when_initiating(self):
        form = SalesBookingActionForm(data={
            'sales_booking_id': self.sales_booking.pk,
            'action': 'reject',
            'initiate_refund': True,
            'refund_amount': None,
        })
        self.assertFalse(form.is_valid())
        self.assertIn('refund_amount', form.errors)
        self.assertIn('Please enter a refund amount if initiating a refund.', form.errors['refund_amount'])

    def test_reject_action_zero_refund_amount_when_initiating(self):
        form = SalesBookingActionForm(data={
            'sales_booking_id': self.sales_booking.pk,
            'action': 'reject',
            'initiate_refund': True,
            'refund_amount': Decimal('0.00'),
        })
        self.assertFalse(form.is_valid())
        self.assertIn('refund_amount', form.errors)
        self.assertIn('Ensure this value is greater than or equal to 0.01.', form.errors['refund_amount'])

    def test_reject_action_negative_refund_amount_when_initiating(self):
        form = SalesBookingActionForm(data={
            'sales_booking_id': self.sales_booking.pk,
            'action': 'reject',
            'initiate_refund': True,
            'refund_amount': Decimal('-10.00'),
        })
        self.assertFalse(form.is_valid())
        self.assertIn('refund_amount', form.errors)
        self.assertIn('Ensure this value is greater than or equal to 0.01.', form.errors['refund_amount'])

    def test_reject_action_refund_amount_exceeds_paid_amount(self):
        form = SalesBookingActionForm(data={
            'sales_booking_id': self.sales_booking.pk,
            'action': 'reject',
            'initiate_refund': True,
            'refund_amount': Decimal('150.00'),
        })
        self.assertFalse(form.is_valid())
        self.assertIn('refund_amount', form.errors)
        self.assertEqual(form.errors['refund_amount'], [f'Refund amount cannot exceed the amount paid ({self.sales_booking.payment.amount:.2f} {self.sales_booking.payment.currency}).'])

    def test_reject_action_refund_amount_without_initiate_refund_checked(self):
        form = SalesBookingActionForm(data={
            'sales_booking_id': self.sales_booking.pk,
            'action': 'reject',
            'initiate_refund': False,
            'refund_amount': Decimal('50.00'),
        })
        self.assertFalse(form.is_valid())
        self.assertIn('initiate_refund', form.errors)
        self.assertEqual(form.errors['initiate_refund'], ['Please check \'Initiate Refund for Deposit\' to specify a refund amount.'])

    def test_reject_action_sales_booking_not_found(self):
        form = SalesBookingActionForm(data={
            'sales_booking_id': 999,
            'action': 'reject',
            'initiate_refund': True,
            'refund_amount': Decimal('50.00'),
        })
        self.assertFalse(form.is_valid())
        self.assertIn('__all__', form.errors)
        self.assertEqual(form.errors['__all__'], ['Sales booking not found.'])

    def test_reject_action_no_valid_payment_for_booking(self):
        form = SalesBookingActionForm(data={
            'sales_booking_id': self.sales_booking_no_payment.pk,
            'action': 'reject',
            'initiate_refund': True,
            'refund_amount': Decimal('50.00'),
        })
        self.assertFalse(form.is_valid())
        self.assertIn('refund_amount', form.errors)
        self.assertEqual(form.errors['refund_amount'], ['Cannot initiate refund: No valid payment found for this booking or amount paid is zero.'])

    def test_reject_action_zero_amount_paid_for_booking(self):
        form = SalesBookingActionForm(data={
            'sales_booking_id': self.sales_booking_zero_payment.pk,
            'action': 'reject',
            'initiate_refund': True,
            'refund_amount': Decimal('50.00'),
        })
        self.assertFalse(form.is_valid())
        self.assertIn('refund_amount', form.errors)
        self.assertEqual(form.errors['refund_amount'], [f'Refund amount cannot exceed the amount paid ({self.sales_booking_zero_payment.payment.amount:.2f} {self.sales_booking_zero_payment.payment.currency}).'])
