from django.test import TestCase
from decimal import Decimal
from payments.utils.update_associated_bookings_and_payments import update_associated_bookings_and_payments
from payments.tests.test_helpers.model_factories import PaymentFactory, ServiceBookingFactory, SalesBookingFactory

class UpdateAssociatedBookingsAndPaymentsTest(TestCase):

    def setUp(self):
        self.initial_amount = Decimal('100.00')
        self.payment = PaymentFactory(amount=self.initial_amount, refunded_amount=Decimal('0.00'), status='succeeded')
        self.service_booking = ServiceBookingFactory(payment=self.payment, amount_paid=self.initial_amount, payment_status='paid', booking_status='confirmed')
        self.sales_booking = SalesBookingFactory(payment=self.payment, amount_paid=self.initial_amount, payment_status='paid', booking_status='confirmed')

    def test_full_refund_service_booking(self):
        total_refunded_amount = self.initial_amount
        update_associated_bookings_and_payments(self.payment, self.service_booking, 'service_booking', total_refunded_amount)

        self.service_booking.refresh_from_db()
        self.payment.refresh_from_db()

        self.assertEqual(self.service_booking.amount_paid, Decimal('0.00'))
        self.assertEqual(self.service_booking.payment_status, 'refunded')
        self.assertEqual(self.payment.refunded_amount, total_refunded_amount)
        self.assertEqual(self.payment.status, 'refunded')

    def test_partial_refund_service_booking(self):
        total_refunded_amount = Decimal('50.00')
        update_associated_bookings_and_payments(self.payment, self.service_booking, 'service_booking', total_refunded_amount)

        self.service_booking.refresh_from_db()
        self.payment.refresh_from_db()

        self.assertEqual(self.service_booking.amount_paid, Decimal('50.00'))
        self.assertEqual(self.service_booking.payment_status, 'partially_refunded')
        self.assertEqual(self.payment.refunded_amount, total_refunded_amount)
        self.assertEqual(self.payment.status, 'partially_refunded')

    def test_no_refund_service_booking(self):
        total_refunded_amount = Decimal('0.00')
        update_associated_bookings_and_payments(self.payment, self.service_booking, 'service_booking', total_refunded_amount)

        self.service_booking.refresh_from_db()
        self.payment.refresh_from_db()

        self.assertEqual(self.service_booking.amount_paid, self.initial_amount)
        self.assertEqual(self.service_booking.payment_status, 'paid')
        self.assertEqual(self.payment.refunded_amount, total_refunded_amount)
        self.assertEqual(self.payment.status, 'succeeded')

    def test_full_refund_sales_booking(self):
        total_refunded_amount = self.initial_amount
        update_associated_bookings_and_payments(self.payment, self.sales_booking, 'sales_booking', total_refunded_amount)

        self.sales_booking.refresh_from_db()
        self.payment.refresh_from_db()

        self.assertEqual(self.sales_booking.amount_paid, Decimal('0.00'))
        self.assertEqual(self.sales_booking.payment_status, 'refunded')
        self.assertEqual(self.payment.refunded_amount, total_refunded_amount)
        self.assertEqual(self.payment.status, 'refunded')

    def test_partial_refund_sales_booking(self):
        total_refunded_amount = Decimal('50.00')
        update_associated_bookings_and_payments(self.payment, self.sales_booking, 'sales_booking', total_refunded_amount)

        self.sales_booking.refresh_from_db()
        self.payment.refresh_from_db()

        self.assertEqual(self.sales_booking.amount_paid, Decimal('50.00'))
        self.assertEqual(self.sales_booking.payment_status, 'partially_refunded')
        self.assertEqual(self.payment.refunded_amount, total_refunded_amount)
        self.assertEqual(self.payment.status, 'partially_refunded')

    def test_no_refund_sales_booking(self):
        total_refunded_amount = Decimal('0.00')
        update_associated_bookings_and_payments(self.payment, self.sales_booking, 'sales_booking', total_refunded_amount)

        self.sales_booking.refresh_from_db()
        self.payment.refresh_from_db()

        self.assertEqual(self.sales_booking.amount_paid, self.initial_amount)
        self.assertEqual(self.sales_booking.payment_status, 'paid')
        self.assertEqual(self.payment.refunded_amount, total_refunded_amount)
        self.assertEqual(self.payment.status, 'succeeded')

    def test_service_booking_status_declined_to_declined_refunded(self):
        self.service_booking.booking_status = 'declined'
        self.service_booking.save()
        total_refunded_amount = self.initial_amount
        update_associated_bookings_and_payments(self.payment, self.service_booking, 'service_booking', total_refunded_amount)
        self.service_booking.refresh_from_db()
        self.assertEqual(self.service_booking.booking_status, 'DECLINED_REFUNDED')

    def test_sales_booking_status_pending_confirmation_to_declined_refunded(self):
        self.sales_booking.booking_status = 'pending_confirmation'
        self.sales_booking.save()
        total_refunded_amount = self.initial_amount
        update_associated_bookings_and_payments(self.payment, self.sales_booking, 'sales_booking', total_refunded_amount)
        self.sales_booking.refresh_from_db()
        self.assertEqual(self.sales_booking.booking_status, 'declined_refunded')

    def test_sales_booking_status_confirmed_to_declined_refunded(self):
        self.sales_booking.booking_status = 'confirmed'
        self.sales_booking.save()
        total_refunded_amount = self.initial_amount
        update_associated_bookings_and_payments(self.payment, self.sales_booking, 'sales_booking', total_refunded_amount)
        self.sales_booking.refresh_from_db()
        self.assertEqual(self.sales_booking.booking_status, 'declined_refunded')

    def test_sales_booking_status_enquired_to_declined_refunded(self):
        self.sales_booking.booking_status = 'enquired'
        self.sales_booking.save()
        total_refunded_amount = self.initial_amount
        update_associated_bookings_and_payments(self.payment, self.sales_booking, 'sales_booking', total_refunded_amount)
        self.sales_booking.refresh_from_db()
        self.assertEqual(self.sales_booking.booking_status, 'declined_refunded')

    def test_sales_booking_status_cancelled_to_declined_refunded(self):
        self.sales_booking.booking_status = 'cancelled'
        self.sales_booking.save()
        total_refunded_amount = self.initial_amount
        update_associated_bookings_and_payments(self.payment, self.sales_booking, 'sales_booking', total_refunded_amount)
        self.sales_booking.refresh_from_db()
        self.assertEqual(self.sales_booking.booking_status, 'declined_refunded')

    def test_sales_booking_status_declined_to_declined_refunded(self):
        self.sales_booking.booking_status = 'declined'
        self.sales_booking.save()
        total_refunded_amount = self.initial_amount
        update_associated_bookings_and_payments(self.payment, self.sales_booking, 'sales_booking', total_refunded_amount)
        self.sales_booking.refresh_from_db()
        self.assertEqual(self.sales_booking.booking_status, 'declined_refunded')

    def test_sales_booking_status_no_show_to_declined_refunded(self):
        self.sales_booking.booking_status = 'no_show'
        self.sales_booking.save()
        total_refunded_amount = self.initial_amount
        update_associated_bookings_and_payments(self.payment, self.sales_booking, 'sales_booking', total_refunded_amount)
        self.sales_booking.refresh_from_db()
        self.assertEqual(self.sales_booking.booking_status, 'declined_refunded')

    def test_no_booking_object(self):
        total_refunded_amount = Decimal('25.00')
        original_payment_status = self.payment.status
        update_associated_bookings_and_payments(self.payment, None, 'unknown', total_refunded_amount)

        self.payment.refresh_from_db()

        self.assertEqual(self.payment.refunded_amount, total_refunded_amount)
        self.assertEqual(self.payment.status, 'partially_refunded')
        self.assertEqual(self.service_booking.amount_paid, self.initial_amount)
        self.assertEqual(self.service_booking.payment_status, 'paid')
        self.assertEqual(self.service_booking.booking_status, 'confirmed')