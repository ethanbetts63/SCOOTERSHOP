from django.test import TestCase
from decimal import Decimal
from payments.utils.update_associated_bookings_and_payments import update_associated_bookings_and_payments
from payments.models import Payment
from service.models import ServiceBooking
from inventory.models import SalesBooking

from service.tests.test_helpers.model_factories import ServiceBookingFactory
from inventory.tests.test_helpers.model_factories import SalesBookingFactory
from payments.tests.test_helpers.model_factories import PaymentFactory

class UpdateAssociatedBookingsAndPaymentsTest(TestCase):

    def setUp(self):
        # Clean up database before each test
        Payment.objects.all().delete()
        ServiceBooking.objects.all().delete()
        SalesBooking.objects.all().delete()

    # --- Service Booking Tests ---
    def test_service_booking_full_refund(self):
        booking = ServiceBookingFactory(amount_paid=Decimal("100.00"), payment_status="paid", booking_status="confirmed")
        payment = PaymentFactory(service_booking=booking, amount=Decimal("100.00"), refunded_amount=Decimal("0.00"), status="succeeded")

        update_associated_bookings_and_payments(payment, booking, "service_booking", Decimal("100.00"))

        booking.refresh_from_db()
        payment.refresh_from_db()

        self.assertEqual(booking.amount_paid, Decimal("0.00"))
        self.assertEqual(booking.payment_status, "refunded")
        self.assertEqual(booking.booking_status, "confirmed") # Should not change unless declined

        self.assertEqual(payment.refunded_amount, Decimal("100.00"))
        self.assertEqual(payment.status, "refunded")

    def test_service_booking_partial_refund(self):
        booking = ServiceBookingFactory(amount_paid=Decimal("100.00"), payment_status="paid", booking_status="confirmed")
        payment = PaymentFactory(service_booking=booking, amount=Decimal("100.00"), refunded_amount=Decimal("0.00"), status="succeeded")

        update_associated_bookings_and_payments(payment, booking, "service_booking", Decimal("50.00"))

        booking.refresh_from_db()
        payment.refresh_from_db()

        self.assertEqual(booking.amount_paid, Decimal("50.00"))
        self.assertEqual(booking.payment_status, "partially_refunded")
        self.assertEqual(booking.booking_status, "confirmed")

        self.assertEqual(payment.refunded_amount, Decimal("50.00"))
        self.assertEqual(payment.status, "partially_refunded")

    def test_service_booking_no_refund(self):
        booking = ServiceBookingFactory(amount_paid=Decimal("100.00"), payment_status="paid", booking_status="confirmed")
        payment = PaymentFactory(service_booking=booking, amount=Decimal("100.00"), refunded_amount=Decimal("0.00"), status="succeeded")

        update_associated_bookings_and_payments(payment, booking, "service_booking", Decimal("0.00"))

        booking.refresh_from_db()
        payment.refresh_from_db()

        self.assertEqual(booking.amount_paid, Decimal("100.00"))
        self.assertEqual(booking.payment_status, "paid")
        self.assertEqual(booking.booking_status, "confirmed")

        self.assertEqual(payment.refunded_amount, Decimal("0.00"))
        self.assertEqual(payment.status, "succeeded")

    def test_service_booking_declined_to_declined_refunded(self):
        booking = ServiceBookingFactory(amount_paid=Decimal("100.00"), payment_status="paid", booking_status="declined")
        payment = PaymentFactory(service_booking=booking, amount=Decimal("100.00"), refunded_amount=Decimal("0.00"), status="succeeded")

        update_associated_bookings_and_payments(payment, booking, "service_booking", Decimal("100.00"))

        booking.refresh_from_db()
        payment.refresh_from_db()

        self.assertEqual(booking.payment_status, "refunded")
        self.assertEqual(booking.booking_status, "DECLINED_REFUNDED")

    # --- Sales Booking Tests ---
    def test_sales_booking_full_refund_from_pending(self):
        booking = SalesBookingFactory(amount_paid=Decimal("100.00"), payment_status="paid", booking_status="pending_confirmation")
        payment = PaymentFactory(sales_booking=booking, amount=Decimal("100.00"), refunded_amount=Decimal("0.00"), status="succeeded")

        update_associated_bookings_and_payments(payment, booking, "sales_booking", Decimal("100.00"))

        booking.refresh_from_db()
        payment.refresh_from_db()

        self.assertEqual(booking.amount_paid, Decimal("0.00"))
        self.assertEqual(booking.payment_status, "refunded")
        self.assertEqual(booking.booking_status, "declined_refunded")

        self.assertEqual(payment.refunded_amount, Decimal("100.00"))
        self.assertEqual(payment.status, "refunded")

    def test_sales_booking_full_refund_from_cancelled(self):
        booking = SalesBookingFactory(amount_paid=Decimal("100.00"), payment_status="paid", booking_status="cancelled")
        payment = PaymentFactory(sales_booking=booking, amount=Decimal("100.00"), refunded_amount=Decimal("0.00"), status="succeeded")

        update_associated_bookings_and_payments(payment, booking, "sales_booking", Decimal("100.00"))

        booking.refresh_from_db()
        payment.refresh_from_db()

        self.assertEqual(booking.payment_status, "refunded")
        self.assertEqual(booking.booking_status, "declined_refunded")

    def test_sales_booking_partial_refund(self):
        booking = SalesBookingFactory(amount_paid=Decimal("100.00"), payment_status="paid", booking_status="confirmed")
        payment = PaymentFactory(sales_booking=booking, amount=Decimal("100.00"), refunded_amount=Decimal("0.00"), status="succeeded")

        update_associated_bookings_and_payments(payment, booking, "sales_booking", Decimal("50.00"))

        booking.refresh_from_db()
        payment.refresh_from_db()

        self.assertEqual(booking.amount_paid, Decimal("50.00"))
        self.assertEqual(booking.payment_status, "partially_refunded")
        self.assertEqual(booking.booking_status, "confirmed") # Should not change

        self.assertEqual(payment.refunded_amount, Decimal("50.00"))
        self.assertEqual(payment.status, "partially_refunded")

    # --- Edge Cases ---
    def test_booking_obj_is_none(self):
        payment = PaymentFactory(amount=Decimal("100.00"), refunded_amount=Decimal("0.00"), status="succeeded")
        
        # Call the function with booking_obj as None
        update_associated_bookings_and_payments(payment, None, "service_booking", Decimal("50.00"))

        payment.refresh_from_db()

        # Only payment object should be updated
        self.assertEqual(payment.refunded_amount, Decimal("50.00"))
        self.assertEqual(payment.status, "partially_refunded")

    def test_payment_refunded_amount_exceeds_original_amount(self):
        booking = ServiceBookingFactory(amount_paid=Decimal("100.00"), payment_status="paid")
        payment = PaymentFactory(service_booking=booking, amount=Decimal("100.00"), refunded_amount=Decimal("0.00"), status="succeeded")

        # Attempt to refund more than originally paid
        update_associated_bookings_and_payments(payment, booking, "service_booking", Decimal("150.00"))

        booking.refresh_from_db()
        payment.refresh_from_db()

        # Booking amount_paid should be 0, payment refunded_amount should be capped at original amount
        self.assertEqual(booking.amount_paid, Decimal("0.00"))
        self.assertEqual(booking.payment_status, "refunded")
        
        self.assertEqual(payment.refunded_amount, Decimal("150.00")) # This will reflect the passed value
        self.assertEqual(payment.status, "refunded")

    def test_payment_status_transitions_correctly(self):
        booking = ServiceBookingFactory(amount_paid=Decimal("100.00"))
        payment = PaymentFactory(service_booking=booking, amount=Decimal("100.00"), refunded_amount=Decimal("0.00"), status="succeeded")

        # Partial refund
        update_associated_bookings_and_payments(payment, booking, "service_booking", Decimal("25.00"))
        payment.refresh_from_db()
        self.assertEqual(payment.status, "partially_refunded")

        # Full refund (cumulative)
        update_associated_bookings_and_payments(payment, booking, "service_booking", Decimal("100.00"))
        payment.refresh_from_db()
        self.assertEqual(payment.status, "refunded")

        # No refund (resetting for test)
        payment.refunded_amount = Decimal("0.00")
        payment.status = "succeeded"
        payment.save()
        update_associated_bookings_and_payments(payment, booking, "service_booking", Decimal("0.00"))
        payment.refresh_from_db()
        self.assertEqual(payment.status, "succeeded")
