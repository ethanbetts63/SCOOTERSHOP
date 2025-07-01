from decimal import Decimal

from django.test import TestCase

                                          
from payments.utils.update_associated_bookings_and_payments import update_associated_bookings_and_payments

                            
from payments.tests.test_helpers.model_factories import (
    PaymentFactory,
    HireBookingFactory,
    ServiceBookingFactory,
    SalesBookingFactory,                            
)


class UpdateAssociatedBookingsAndPaymentsTestCase(TestCase):
    """
    Tests for the update_associated_bookings_and_payments utility function.
    This suite covers updates to booking and payment statuses and amounts
    based on refund activity.
    """

    def test_full_refund_hire_booking(self):
        """
        Tests full refund scenario for a HireBooking.
        - Booking amount_paid should be 0.
        - Booking payment_status should be 'refunded'.
        - Booking status should be 'cancelled'.
        - Payment refunded_amount should match total_refunded_amount.
        - Payment status should be 'refunded'.
        """
        initial_amount = Decimal('100.00')
        hire_booking = HireBookingFactory(amount_paid=initial_amount, payment_status='paid', status='confirmed')
        payment = PaymentFactory(
            hire_booking=hire_booking,
            service_booking=None,
            sales_booking=None,                              
            amount=initial_amount,
            status='succeeded',
            refunded_amount=Decimal('0.00')
        )
        total_refunded_amount = initial_amount              

        update_associated_bookings_and_payments(payment, hire_booking, 'hire_booking', total_refunded_amount)

                                                       
        hire_booking.refresh_from_db()
        payment.refresh_from_db()

                                    
        self.assertEqual(hire_booking.amount_paid, Decimal('0.00'))
        self.assertEqual(hire_booking.payment_status, 'refunded')
        self.assertEqual(hire_booking.status, 'cancelled')                                       

                                
        self.assertEqual(payment.refunded_amount, total_refunded_amount)
        self.assertEqual(payment.status, 'refunded')

    def test_partial_refund_hire_booking(self):
        """
        Tests partial refund scenario for a HireBooking.
        - Booking amount_paid should be reduced.
        - Booking payment_status should be 'partially_refunded'.
        - Booking status should remain 'confirmed'.
        - Payment refunded_amount should match total_refunded_amount.
        - Payment status should be 'partially_refunded'.
        """
        initial_amount = Decimal('100.00')
        refund_amount = Decimal('40.00')
        hire_booking = HireBookingFactory(amount_paid=initial_amount, payment_status='paid', status='confirmed')
        payment = PaymentFactory(
            hire_booking=hire_booking,
            service_booking=None,
            sales_booking=None,                              
            amount=initial_amount,
            status='succeeded',
            refunded_amount=Decimal('0.00')
        )
        total_refunded_amount = refund_amount

        update_associated_bookings_and_payments(payment, hire_booking, 'hire_booking', total_refunded_amount)

        hire_booking.refresh_from_db()
        payment.refresh_from_db()

                                    
        self.assertEqual(hire_booking.amount_paid, initial_amount - refund_amount)
        self.assertEqual(hire_booking.payment_status, 'partially_refunded')
        self.assertEqual(hire_booking.status, 'confirmed')                                             

                                
        self.assertEqual(payment.refunded_amount, total_refunded_amount)
        self.assertEqual(payment.status, 'partially_refunded')

    def test_no_refund_hire_booking(self):
        """
        Tests no refund scenario for a HireBooking (ensure statuses remain 'paid').
        """
        initial_amount = Decimal('100.00')
        hire_booking = HireBookingFactory(amount_paid=initial_amount, payment_status='paid', status='confirmed')
        payment = PaymentFactory(
            hire_booking=hire_booking,
            service_booking=None,
            sales_booking=None,                              
            amount=initial_amount,
            status='succeeded',
            refunded_amount=Decimal('0.00')
        )
        total_refunded_amount = Decimal('0.00')

        update_associated_bookings_and_payments(payment, hire_booking, 'hire_booking', total_refunded_amount)

        hire_booking.refresh_from_db()
        payment.refresh_from_db()

                                    
        self.assertEqual(hire_booking.amount_paid, initial_amount)
        self.assertEqual(hire_booking.payment_status, 'paid')
        self.assertEqual(hire_booking.status, 'confirmed')

                                
        self.assertEqual(payment.refunded_amount, total_refunded_amount)
        self.assertEqual(payment.status, 'succeeded')


    def test_full_refund_service_booking(self):
        """
        Tests full refund scenario for a ServiceBooking.
        - Booking amount_paid should be 0.
        - Booking payment_status should be 'refunded'.
        - Booking status should remain as is, unless 'declined'.
        - Payment refunded_amount should match total_refunded_amount.
        - Payment status should be 'refunded'.
        """
        initial_amount = Decimal('150.00')
        service_booking = ServiceBookingFactory(amount_paid=initial_amount, payment_status='paid', booking_status='pending')
        payment = PaymentFactory(
            hire_booking=None,
            service_booking=service_booking,
            sales_booking=None,                              
            amount=initial_amount,
            status='succeeded',
            refunded_amount=Decimal('0.00')
        )
        total_refunded_amount = initial_amount

        update_associated_bookings_and_payments(payment, service_booking, 'service_booking', total_refunded_amount)

        service_booking.refresh_from_db()
        payment.refresh_from_db()

                                       
        self.assertEqual(service_booking.amount_paid, Decimal('0.00'))
        self.assertEqual(service_booking.payment_status, 'refunded')
        self.assertEqual(service_booking.booking_status, 'pending')                                    

                                
        self.assertEqual(payment.refunded_amount, total_refunded_amount)
        self.assertEqual(payment.status, 'refunded')

    def test_partial_refund_service_booking(self):
        """
        Tests partial refund scenario for a ServiceBooking.
        - Booking amount_paid should be reduced.
        - Booking payment_status should be 'partially_refunded'.
        - Booking status should remain unchanged.
        - Payment refunded_amount should match total_refunded_amount.
        - Payment status should be 'partially_refunded'.
        """
        initial_amount = Decimal('150.00')
        refund_amount = Decimal('70.00')
        service_booking = ServiceBookingFactory(amount_paid=initial_amount, payment_status='paid', booking_status='accepted')
        payment = PaymentFactory(
            hire_booking=None,
            service_booking=service_booking,
            sales_booking=None,                              
            amount=initial_amount,
            status='succeeded',
            refunded_amount=Decimal('0.00')
        )
        total_refunded_amount = refund_amount

        update_associated_bookings_and_payments(payment, service_booking, 'service_booking', total_refunded_amount)

        service_booking.refresh_from_db()
        payment.refresh_from_db()

                                       
        self.assertEqual(service_booking.amount_paid, initial_amount - refund_amount)
        self.assertEqual(service_booking.payment_status, 'partially_refunded')
        self.assertEqual(service_booking.booking_status, 'accepted')

                                
        self.assertEqual(payment.refunded_amount, total_refunded_amount)
        self.assertEqual(payment.status, 'partially_refunded')

    def test_service_booking_declined_and_fully_refunded(self):
        """
        Tests specific scenario for ServiceBooking:
        If booking_status is 'declined' and payment_status becomes 'refunded',
        booking_status should change to 'DECLINED_REFUNDED'.
        """
        initial_amount = Decimal('200.00')
        service_booking = ServiceBookingFactory(amount_paid=initial_amount, payment_status='paid', booking_status='declined')
        payment = PaymentFactory(
            hire_booking=None,
            service_booking=service_booking,
            sales_booking=None,                              
            amount=initial_amount,
            status='succeeded',
            refunded_amount=Decimal('0.00')
        )
        total_refunded_amount = initial_amount              

        update_associated_bookings_and_payments(payment, service_booking, 'service_booking', total_refunded_amount)

        service_booking.refresh_from_db()
        payment.refresh_from_db()

                                       
        self.assertEqual(service_booking.amount_paid, Decimal('0.00'))
        self.assertEqual(service_booking.payment_status, 'refunded')
        self.assertEqual(service_booking.booking_status, 'DECLINED_REFUNDED')                           

                                
        self.assertEqual(payment.refunded_amount, total_refunded_amount)
        self.assertEqual(payment.status, 'refunded')

                                        

    def test_full_refund_sales_booking_from_initial_status(self):
        """
        Tests full refund for a SalesBooking when its initial status is
        'pending_confirmation', 'confirmed', or 'enquired'.
        Booking status should transition to 'declined_refunded'.
        """
        initial_amount = Decimal('300.00')
                                          
        sales_booking = SalesBookingFactory(amount_paid=initial_amount, payment_status='deposit_paid', booking_status='pending_confirmation')
        payment = PaymentFactory(
            sales_booking=sales_booking,
            hire_booking=None,
            service_booking=None,
            amount=initial_amount,
            status='succeeded',
            refunded_amount=Decimal('0.00')
        )
        total_refunded_amount = initial_amount              

        update_associated_bookings_and_payments(payment, sales_booking, 'sales_booking', total_refunded_amount)

        sales_booking.refresh_from_db()
        payment.refresh_from_db()

        self.assertEqual(sales_booking.amount_paid, Decimal('0.00'))
        self.assertEqual(sales_booking.payment_status, 'refunded')
        self.assertEqual(sales_booking.booking_status, 'declined_refunded')                  

        self.assertEqual(payment.refunded_amount, total_refunded_amount)
        self.assertEqual(payment.status, 'refunded')

                                                  
        sales_booking_2 = SalesBookingFactory(amount_paid=initial_amount, payment_status='deposit_paid', booking_status='confirmed')
        payment_2 = PaymentFactory(
            sales_booking=sales_booking_2,
            hire_booking=None,
            service_booking=None,
            amount=initial_amount,
            status='succeeded',
            refunded_amount=Decimal('0.00')
        )
        update_associated_bookings_and_payments(payment_2, sales_booking_2, 'sales_booking', total_refunded_amount)
        sales_booking_2.refresh_from_db()
        self.assertEqual(sales_booking_2.booking_status, 'declined_refunded')

                                                 
        sales_booking_3 = SalesBookingFactory(amount_paid=initial_amount, payment_status='unpaid', booking_status='enquired')                              
        payment_3 = PaymentFactory(
            sales_booking=sales_booking_3,
            hire_booking=None,
            service_booking=None,
            amount=initial_amount,                                 
            status='succeeded',                                                                                        
            refunded_amount=Decimal('0.00')
        )
                                                                                                                             
                                                                                                      
                                                                                                                     
        sales_booking_3.amount_paid = initial_amount                                                
        sales_booking_3.payment_status = 'paid'
        sales_booking_3.save()

        update_associated_bookings_and_payments(payment_3, sales_booking_3, 'sales_booking', initial_amount)              
        sales_booking_3.refresh_from_db()
        self.assertEqual(sales_booking_3.booking_status, 'declined_refunded')


    def test_full_refund_sales_booking_from_already_cancelled_status(self):
        """
        Tests full refund for a SalesBooking when its initial status is
        'cancelled', 'declined', or 'no_show'.
        Booking status should still transition to 'declined_refunded'.
        """
        initial_amount = Decimal('250.00')
                               
        sales_booking = SalesBookingFactory(amount_paid=initial_amount, payment_status='paid', booking_status='cancelled')
        payment = PaymentFactory(
            sales_booking=sales_booking,
            hire_booking=None,
            service_booking=None,
            amount=initial_amount,
            status='succeeded',
            refunded_amount=Decimal('0.00')
        )
        total_refunded_amount = initial_amount              

        update_associated_bookings_and_payments(payment, sales_booking, 'sales_booking', total_refunded_amount)

        sales_booking.refresh_from_db()
        payment.refresh_from_db()

        self.assertEqual(sales_booking.amount_paid, Decimal('0.00'))
        self.assertEqual(sales_booking.payment_status, 'refunded')
        self.assertEqual(sales_booking.booking_status, 'declined_refunded')                      

        self.assertEqual(payment.refunded_amount, total_refunded_amount)
        self.assertEqual(payment.status, 'refunded')

                                                 
        sales_booking_2 = SalesBookingFactory(amount_paid=initial_amount, payment_status='paid', booking_status='declined')
        payment_2 = PaymentFactory(
            sales_booking=sales_booking_2,
            hire_booking=None,
            service_booking=None,
            amount=initial_amount,
            status='succeeded',
            refunded_amount=Decimal('0.00')
        )
        update_associated_bookings_and_payments(payment_2, sales_booking_2, 'sales_booking', total_refunded_amount)
        sales_booking_2.refresh_from_db()
        self.assertEqual(sales_booking_2.booking_status, 'declined_refunded')

                                                
        sales_booking_3 = SalesBookingFactory(amount_paid=initial_amount, payment_status='paid', booking_status='no_show')
        payment_3 = PaymentFactory(
            sales_booking=sales_booking_3,
            hire_booking=None,
            service_booking=None,
            amount=initial_amount,
            status='succeeded',
            refunded_amount=Decimal('0.00')
        )
        update_associated_bookings_and_payments(payment_3, sales_booking_3, 'sales_booking', total_refunded_amount)
        sales_booking_3.refresh_from_db()
        self.assertEqual(sales_booking_3.booking_status, 'declined_refunded')


    def test_partial_refund_sales_booking(self):
        """
        Tests partial refund scenario for a SalesBooking.
        - Booking amount_paid should be reduced.
        - Booking payment_status should be 'partially_refunded'.
        - Booking status should remain unchanged (e.g., 'confirmed').
        - Payment refunded_amount should match total_refunded_amount.
        - Payment status should be 'partially_refunded'.
        """
        initial_amount = Decimal('300.00')
        refund_amount = Decimal('100.00')
        sales_booking = SalesBookingFactory(amount_paid=initial_amount, payment_status='paid', booking_status='confirmed')
        payment = PaymentFactory(
            sales_booking=sales_booking,
            hire_booking=None,
            service_booking=None,
            amount=initial_amount,
            status='succeeded',
            refunded_amount=Decimal('0.00')
        )
        total_refunded_amount = refund_amount

        update_associated_bookings_and_payments(payment, sales_booking, 'sales_booking', total_refunded_amount)

        sales_booking.refresh_from_db()
        payment.refresh_from_db()

        self.assertEqual(sales_booking.amount_paid, initial_amount - refund_amount)
        self.assertEqual(sales_booking.payment_status, 'partially_refunded')
        self.assertEqual(sales_booking.booking_status, 'confirmed')                          

        self.assertEqual(payment.refunded_amount, total_refunded_amount)
        self.assertEqual(payment.status, 'partially_refunded')


    def test_no_refund_sales_booking(self):
        """
        Tests no refund scenario for a SalesBooking (ensure statuses remain 'paid'/'succeeded').
        """
        initial_amount = Decimal('300.00')
        sales_booking = SalesBookingFactory(amount_paid=initial_amount, payment_status='paid', booking_status='confirmed')
        payment = PaymentFactory(
            sales_booking=sales_booking,
            hire_booking=None,
            service_booking=None,
            amount=initial_amount,
            status='succeeded',
            refunded_amount=Decimal('0.00')
        )
        total_refunded_amount = Decimal('0.00')

        update_associated_bookings_and_payments(payment, sales_booking, 'sales_booking', total_refunded_amount)

        sales_booking.refresh_from_db()
        payment.refresh_from_db()

        self.assertEqual(sales_booking.amount_paid, initial_amount)
        self.assertEqual(sales_booking.payment_status, 'paid')
        self.assertEqual(sales_booking.booking_status, 'confirmed')

        self.assertEqual(payment.refunded_amount, total_refunded_amount)
        self.assertEqual(payment.status, 'succeeded')


    def test_payment_updates_only_when_no_booking_obj(self):
        """
        Tests that if no booking_obj is provided, only the payment object is updated.
        """
        initial_amount = Decimal('50.00')
        payment = PaymentFactory(
            hire_booking=None,
            service_booking=None,
            sales_booking=None,                              
            amount=initial_amount,
            status='succeeded',
            refunded_amount=Decimal('0.00')
        )
        total_refunded_amount = Decimal('25.00')

                                                                      
        update_associated_bookings_and_payments(payment, None, 'unknown', total_refunded_amount)

        payment.refresh_from_db()

                                
        self.assertEqual(payment.refunded_amount, total_refunded_amount)
        self.assertEqual(payment.status, 'partially_refunded')
        
                                                                                      


    def test_payment_status_updates_from_partially_refunded_to_refunded(self):
        """
        Tests that if payment was partially refunded and then fully refunded.
        """
        initial_amount = Decimal('100.00')
        payment = PaymentFactory(
            amount=initial_amount,
            status='partially_refunded',
            refunded_amount=Decimal('20.00')
        )
        total_refunded_amount = initial_amount

        update_associated_bookings_and_payments(payment, None, 'unknown', total_refunded_amount)
        payment.refresh_from_db()
        self.assertEqual(payment.status, 'refunded')
        self.assertEqual(payment.refunded_amount, initial_amount)

    def test_payment_status_updates_from_succeeded_to_partially_refunded(self):
        """
        Tests that if payment was succeeded and then partially refunded.
        """
        initial_amount = Decimal('100.00')
        payment = PaymentFactory(
            amount=initial_amount,
            status='succeeded',
            refunded_amount=Decimal('0.00')
        )
        total_refunded_amount = Decimal('50.00')

        update_associated_bookings_and_payments(payment, None, 'unknown', total_refunded_amount)
        payment.refresh_from_db()
        self.assertEqual(payment.status, 'partially_refunded')
        self.assertEqual(payment.refunded_amount, total_refunded_amount)

    def test_booking_amount_paid_goes_to_zero_exactly(self):
        """
        Tests that if total refunded amount equals payment amount, amount_paid is 0.
        """
        initial_amount = Decimal('75.00')
        hire_booking = HireBookingFactory(amount_paid=initial_amount, payment_status='paid')
        payment = PaymentFactory(hire_booking=hire_booking, amount=initial_amount, status='succeeded')
        total_refunded_amount = Decimal('75.00')

        update_associated_bookings_and_payments(payment, hire_booking, 'hire_booking', total_refunded_amount)
        hire_booking.refresh_from_db()
        payment.refresh_from_db()

        self.assertEqual(hire_booking.amount_paid, Decimal('0.00'))
        self.assertEqual(hire_booking.payment_status, 'refunded')
        self.assertEqual(payment.refunded_amount, total_refunded_amount)
        self.assertEqual(payment.status, 'refunded')

    def test_booking_amount_paid_negative_due_to_over_refund(self):
        """
        Tests scenario where total refunded amount is greater than original payment.
        Amount paid should still be 0, payment status refunded.
        """
        initial_amount = Decimal('50.00')
        hire_booking = HireBookingFactory(amount_paid=initial_amount, payment_status='paid')
        payment = PaymentFactory(hire_booking=hire_booking, amount=initial_amount, status='succeeded')
        total_refunded_amount = Decimal('60.00')              

        update_associated_bookings_and_payments(payment, hire_booking, 'hire_booking', total_refunded_amount)
        hire_booking.refresh_from_db()
        payment.refresh_from_db()

        self.assertEqual(hire_booking.amount_paid, Decimal('0.00'))                         
        self.assertEqual(hire_booking.payment_status, 'refunded')
        self.assertEqual(payment.refunded_amount, total_refunded_amount)                                  
        self.assertEqual(payment.status, 'refunded')


    def test_booking_status_not_declined_remains_unchanged_on_full_refund_service_booking(self):
        """
        Tests that a ServiceBooking's booking_status does NOT change to 'DECLINED_REFUNDED'
        if its initial status is not 'declined', even on full refund.
        """
        initial_amount = Decimal('100.00')
        service_booking = ServiceBookingFactory(amount_paid=initial_amount, payment_status='paid', booking_status='confirmed')                 
        payment = PaymentFactory(
            hire_booking=None,
            service_booking=service_booking,
            sales_booking=None,                              
            amount=initial_amount,
            status='succeeded',
            refunded_amount=Decimal('0.00')
        )
        total_refunded_amount = initial_amount              

        update_associated_bookings_and_payments(payment, service_booking, 'service_booking', total_refunded_amount)

        service_booking.refresh_from_db()
        self.assertEqual(service_booking.booking_status, 'confirmed')                            
        self.assertEqual(service_booking.payment_status, 'refunded')


    def test_booking_status_not_paid_remains_unchanged_on_full_refund_hire_booking(self):
        """
        Tests that a HireBooking's status changes to 'cancelled' only if payment_status becomes 'refunded'.
        If it was already cancelled, it should remain cancelled.
        """
        initial_amount = Decimal('100.00')
        hire_booking = HireBookingFactory(amount_paid=initial_amount, payment_status='paid', status='pending_approval')                  
        payment = PaymentFactory(
            hire_booking=hire_booking,
            service_booking=None,                              
            sales_booking=None,                              
            amount=initial_amount,
            status='succeeded',
            refunded_amount=Decimal('0.00')
        )
        total_refunded_amount = initial_amount              

        update_associated_bookings_and_payments(payment, hire_booking, 'hire_booking', total_refunded_amount)

        hire_booking.refresh_from_db()
        self.assertEqual(hire_booking.status, 'cancelled')                               
        self.assertEqual(hire_booking.payment_status, 'refunded')

