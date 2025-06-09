from django.test import TestCase

# Import the utility function to be tested
from payments.utils.get_booking_from_payment import get_booking_from_payment

# Import the factories for creating test data
from payments.tests.test_helpers.model_factories import PaymentFactory, HireBookingFactory, ServiceBookingFactory

class GetBookingFromPaymentTestCase(TestCase):
    """
    Tests for the get_booking_from_payment utility function.
    This function should correctly identify and return the associated booking
    object (either HireBooking or ServiceBooking) and its type.
    """

    def test_payment_linked_to_hire_booking(self):
        """
        Tests that get_booking_from_payment correctly returns a HireBooking
        when the payment is linked to one.
        """
        # Create a HireBooking instance
        hire_booking = HireBookingFactory()
        
        # Create a Payment instance linked to the HireBooking
        payment = PaymentFactory(hire_booking=hire_booking, service_booking=None)

        # Call the utility function
        booking_obj, booking_type = get_booking_from_payment(payment)

        # Assert that the correct booking object and type are returned
        self.assertEqual(booking_obj, hire_booking)
        self.assertEqual(booking_type, 'hire_booking')

    def test_payment_linked_to_service_booking(self):
        """
        Tests that get_booking_from_payment correctly returns a ServiceBooking
        when the payment is linked to one.
        """
        # Create a ServiceBooking instance
        service_booking = ServiceBookingFactory()
        
        # Create a Payment instance linked to the ServiceBooking
        payment = PaymentFactory(service_booking=service_booking, hire_booking=None)

        # Call the utility function
        booking_obj, booking_type = get_booking_from_payment(payment)

        # Assert that the correct booking object and type are returned
        self.assertEqual(booking_obj, service_booking)
        self.assertEqual(booking_type, 'service_booking')

    def test_payment_not_linked_to_any_booking(self):
        """
        Tests that get_booking_from_payment returns (None, None) when the
        payment is not linked to either a HireBooking or a ServiceBooking.
        """
        # Create a Payment instance not linked to any booking
        payment = PaymentFactory(hire_booking=None, service_booking=None)

        # Call the utility function
        booking_obj, booking_type = get_booking_from_payment(payment)

        # Assert that (None, None) is returned
        self.assertIsNone(booking_obj)
        self.assertIsNone(booking_type)

    def test_payment_linked_to_both_bookings(self):
        """
        Tests that get_booking_from_payment prioritizes HireBooking if both
        are linked (based on the function's current logic).
        NOTE: In a real application, a Payment should ideally only link to one
        type of booking. This test validates the current function's behavior
        for this edge case.
        """
        hire_booking = HireBookingFactory()
        service_booking = ServiceBookingFactory()

        # Create a Payment linked to both (for testing the function's logic)
        payment = PaymentFactory(hire_booking=hire_booking, service_booking=service_booking)

        # Call the utility function
        booking_obj, booking_type = get_booking_from_payment(payment)

        # Assert that HireBooking is prioritized as per the function's if-elif structure
        self.assertEqual(booking_obj, hire_booking)
        self.assertEqual(booking_type, 'hire_booking')

