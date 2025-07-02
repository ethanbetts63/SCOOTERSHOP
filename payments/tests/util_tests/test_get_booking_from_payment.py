from django.test import TestCase

                                          
from payments.utils.get_booking_from_payment import get_booking_from_payment

                                             
from payments.tests.test_helpers.model_factories import PaymentFactory, ServiceBookingFactory, SalesBookingFactory                            

class GetBookingFromPaymentTestCase(TestCase):
    #--
    def test_payment_linked_to_service_booking(self):
        #--
                                          
        service_booking = ServiceBookingFactory()
        
                                                                
        payment = PaymentFactory(service_booking=service_booking, sales_booking=None)                                

                                   
        booking_obj, booking_type = get_booking_from_payment(payment)

                                                                      
        self.assertEqual(booking_obj, service_booking)
        self.assertEqual(booking_type, 'service_booking')

    def test_payment_linked_to_sales_booking(self):
        #--
                                        
        sales_booking = SalesBookingFactory()
        
                                                              
        payment = PaymentFactory(sales_booking=sales_booking, service_booking=None)                                

                                   
        booking_obj, booking_type = get_booking_from_payment(payment)

                                                                      
        self.assertEqual(booking_obj, sales_booking)
        self.assertEqual(booking_type, 'sales_booking')


    def test_payment_not_linked_to_any_booking(self):
        #--
                                                             
        payment = PaymentFactory(service_booking=None, sales_booking=None)

                                   
        booking_obj, booking_type = get_booking_from_payment(payment)

                                              
        self.assertIsNone(booking_obj)
        self.assertIsNone(booking_type)

    def test_payment_linked_to_multiple_bookings_prioritization(self):
        service_booking = ServiceBookingFactory()
        sales_booking = SalesBookingFactory()
                                                    
        payment_ss = PaymentFactory(service_booking=service_booking, sales_booking=sales_booking)
        booking_obj, booking_type = get_booking_from_payment(payment_ss)
        self.assertEqual(booking_obj, service_booking)
        self.assertEqual(booking_type, 'service_booking')

                                                     
        payment_s = PaymentFactory(service_booking=None, sales_booking=sales_booking)
        booking_obj, booking_type = get_booking_from_payment(payment_s)
        self.assertEqual(booking_obj, sales_booking)
        self.assertEqual(booking_type, 'sales_booking')
