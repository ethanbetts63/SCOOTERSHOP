from django.test import TestCase
from payments.utils.get_booking_from_payment import get_booking_from_payment
from payments.models import Payment
from service.models import ServiceBooking
from inventory.models import SalesBooking

# Import factories from refunds app
from payments.tests.test_helpers.model_factories import PaymentFactory
from service.tests.test_helpers.model_factories import ServiceBookingFactory
from inventory.tests.test_helpers.model_factories import SalesBookingFactory


class GetBookingFromPaymentTest(TestCase):
    def setUp(self):
        # Clean up database before each test
        Payment.objects.all().delete()
        ServiceBooking.objects.all().delete()
        SalesBooking.objects.all().delete()

    def test_get_service_booking_from_payment(self):
        service_booking = ServiceBookingFactory()
        payment = PaymentFactory(service_booking=service_booking)

        booking, booking_type = get_booking_from_payment(payment)

        self.assertEqual(booking, service_booking)
        self.assertEqual(booking_type, "service_booking")

    def test_get_sales_booking_from_payment(self):
        sales_booking = SalesBookingFactory()
        payment = PaymentFactory(sales_booking=sales_booking)

        booking, booking_type = get_booking_from_payment(payment)

        self.assertEqual(booking, sales_booking)
        self.assertEqual(booking_type, "sales_booking")

    def test_get_no_booking_from_payment(self):
        payment = PaymentFactory(service_booking=None, sales_booking=None)

        booking, booking_type = get_booking_from_payment(payment)

        self.assertIsNone(booking)
        self.assertIsNone(booking_type)

    def test_payment_with_both_bookings_prefers_service(self):
        # This scenario should ideally not happen in a well-managed system,
        # but we test the current logic's behavior.
        service_booking = ServiceBookingFactory()
        sales_booking = SalesBookingFactory()
        payment = PaymentFactory(
            service_booking=service_booking, sales_booking=sales_booking
        )

        booking, booking_type = get_booking_from_payment(payment)

        # Current implementation prioritizes service_booking if both are present
        self.assertEqual(booking, service_booking)
        self.assertEqual(booking_type, "service_booking")
