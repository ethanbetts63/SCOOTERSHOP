from django.test import TestCase

# Import the utility function to be tested
from payments.utils.get_booking_from_payment import get_booking_from_payment

# Import the factories for creating test data
from payments.tests.test_helpers.model_factories import PaymentFactory, HireBookingFactory, ServiceBookingFactory, SalesBookingFactory # Added SalesBookingFactory

class GetBookingFromPaymentTestCase(TestCase):
    """
    Tests for the get_booking_from_payment utility function.
    This function should correctly identify and return the associated booking
    object (either HireBooking, ServiceBooking, or SalesBooking) and its type.
    """

    def test_payment_linked_to_hire_booking(self):
        """
        Tests that get_booking_from_payment correctly returns a HireBooking
        when the payment is linked to one.
        """
        # Create a HireBooking instance
        hire_booking = HireBookingFactory()
        
        # Create a Payment instance linked to the HireBooking
        payment = PaymentFactory(hire_booking=hire_booking, service_booking=None, sales_booking=None) # Explicitly set others to None

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
        payment = PaymentFactory(service_booking=service_booking, hire_booking=None, sales_booking=None) # Explicitly set others to None

        # Call the utility function
        booking_obj, booking_type = get_booking_from_payment(payment)

        # Assert that the correct booking object and type are returned
        self.assertEqual(booking_obj, service_booking)
        self.assertEqual(booking_type, 'service_booking')

    def test_payment_linked_to_sales_booking(self):
        """
        Tests that get_booking_from_payment correctly returns a SalesBooking
        when the payment is linked to one.
        This is a new test case to cover the sales_booking integration.
        """
        # Create a SalesBooking instance
        sales_booking = SalesBookingFactory()
        
        # Create a Payment instance linked to the SalesBooking
        payment = PaymentFactory(sales_booking=sales_booking, hire_booking=None, service_booking=None) # Explicitly set others to None

        # Call the utility function
        booking_obj, booking_type = get_booking_from_payment(payment)

        # Assert that the correct booking object and type are returned
        self.assertEqual(booking_obj, sales_booking)
        self.assertEqual(booking_type, 'sales_booking')


    def test_payment_not_linked_to_any_booking(self):
        """
        Tests that get_booking_from_payment returns (None, None) when the
        payment is not linked to any booking type.
        """
        # Create a Payment instance not linked to any booking
        payment = PaymentFactory(hire_booking=None, service_booking=None, sales_booking=None)

        # Call the utility function
        booking_obj, booking_type = get_booking_from_payment(payment)

        # Assert that (None, None) is returned
        self.assertIsNone(booking_obj)
        self.assertIsNone(booking_type)

    def test_payment_linked_to_multiple_bookings_prioritization(self):
        """
        Tests that get_booking_from_payment prioritizes HireBooking, then ServiceBooking,
        then SalesBooking if multiple are linked (based on the function's if-elif structure).
        NOTE: In a real application, a Payment should ideally only link to one
        type of booking. This test validates the current function's behavior
        for this edge case.
        """
        hire_booking = HireBookingFactory()
        service_booking = ServiceBookingFactory()
        sales_booking = SalesBookingFactory()

        # Test HireBooking prioritization (Hire + Service + Sales)
        payment_hss = PaymentFactory(hire_booking=hire_booking, service_booking=service_booking, sales_booking=sales_booking)
        booking_obj, booking_type = get_booking_from_payment(payment_hss)
        self.assertEqual(booking_obj, hire_booking)
        self.assertEqual(booking_type, 'hire_booking')

        # Test ServiceBooking prioritization (Service + Sales, no Hire)
        payment_ss = PaymentFactory(hire_booking=None, service_booking=service_booking, sales_booking=sales_booking)
        booking_obj, booking_type = get_booking_from_payment(payment_ss)
        self.assertEqual(booking_obj, service_booking)
        self.assertEqual(booking_type, 'service_booking')

        # Test SalesBooking only (no Hire or Service)
        payment_s = PaymentFactory(hire_booking=None, service_booking=None, sales_booking=sales_booking)
        booking_obj, booking_type = get_booking_from_payment(payment_s)
        self.assertEqual(booking_obj, sales_booking)
        self.assertEqual(booking_type, 'sales_booking')
