                                                              

# from django.test import TestCase
# from unittest.mock import patch, MagicMock
# from decimal import Decimal                
# from payments.webhook_handlers.refund_handlers import handle_booking_refunded, handle_booking_refund_updated  
# from payments.tests.test_helpers.model_factories import (
#     PaymentFactory, ServiceBookingFactory, SalesBookingFactory,                            
#     RefundRequestFactory, UserFactory, SalesProfileFactory,                            
#     ServiceProfileFactory, MotorcycleFactory, ServiceTypeFactory, CustomerMotorcycleFactory
# )


# class RefundHandlersTests(TestCase):
#     """
#     Tests for the refund webhook handlers in payments/webhook_handlers/refund_handlers.py.
#     """

#     def setUp(self):
#         """
#         Set up common data for tests.
#         We'll mock the utility functions for isolation.
#         """
#         self.mock_get_booking_from_payment = patch('payments.webhook_handlers.refund_handlers.get_booking_from_payment').start()
#         self.mock_extract_stripe_refund_data = patch('payments.webhook_handlers.refund_handlers.extract_stripe_refund_data').start()
#         self.mock_update_associated_bookings_and_payments = patch('payments.webhook_handlers.refund_handlers.update_associated_bookings_and_payments').start()
#         self.mock_process_refund_request_entry = patch('payments.webhook_handlers.refund_handlers.process_refund_request_entry').start()
#         self.mock_send_refund_notifications = patch('payments.webhook_handlers.refund_handlers.send_refund_notifications').start()
                                                          

                                              
#         self.user = UserFactory()
#         self.driver_profile = DriverProfileFactory(user=self.user)
#         self.motorcycle = MotorcycleFactory()
        
                                                                      
#         self.payment = PaymentFactory(amount=Decimal('100.00'), refunded_amount=Decimal('0.00')) 

                            
#         self.hire_booking = HireBookingFactory(
#             payment=self.payment,                                       
#             driver_profile=self.driver_profile, 
#             motorcycle=self.motorcycle
#         )
        
                               
#         self.service_profile = ServiceProfileFactory(user=self.user)
#         self.customer_motorcycle = CustomerMotorcycleFactory(service_profile=self.service_profile)
#         self.service_type = ServiceTypeFactory()
#         self.service_booking = ServiceBookingFactory(
#             payment=self.payment,                                          
#             service_profile=self.service_profile, 
#             customer_motorcycle=self.customer_motorcycle, 
#             service_type=self.service_type
#         )

                             
#         self.sales_profile = SalesProfileFactory(user=self.user)
#         self.sales_booking = SalesBookingFactory(
#             payment=self.payment,                                        
#             sales_profile=self.sales_profile,
#             motorcycle=self.motorcycle
#         )
        
#         self.refund_request = RefundRequestFactory()                                    

                                                                  
#         self.mock_extract_stripe_refund_data.return_value = {
#             'refunded_amount_decimal': Decimal('50.00'),
#             'is_charge_object': True,
#             'is_refund_object': False,
#             'is_payment_intent_object': False,                             
#             'refund_id': 're_test_id',
#             'charge_id': 'ch_test_id',
#         }
                                                           
#         self.mock_get_booking_from_payment.return_value = (self.hire_booking, 'hire')
#         self.mock_process_refund_request_entry.return_value = self.refund_request

#     def tearDown(self):
#         """
#         Stop all patched mocks that were started in setUp.
#         """
#         patch.stopall()

#     def test_handle_booking_refunded_full_flow(self):
#         """
#         Tests the full flow of handle_booking_refunded for a valid refund (Hire Booking).
#         """
#         event_data = {'id': 'evt_test', 'object': 'event'}

#         with patch('django.db.transaction.atomic') as mock_atomic:
                                                               
#             mock_atomic.return_value.__enter__.return_value = MagicMock()
            
#             handle_booking_refunded(self.payment, event_data)

#             mock_atomic.assert_called_once()
#             self.mock_extract_stripe_refund_data.assert_called_once_with(event_data)
#             self.mock_get_booking_from_payment.assert_called_once_with(self.payment)
#             self.mock_update_associated_bookings_and_payments.assert_called_once_with(
#                 self.payment,
#                 self.hire_booking,
#                 'hire',
#                 Decimal('50.00')
#             )
#             self.mock_process_refund_request_entry.assert_called_once_with(
#                 self.payment,
#                 self.hire_booking,
#                 'hire',
#                 self.mock_extract_stripe_refund_data.return_value
#             )
#             self.mock_send_refund_notifications.assert_called_once_with(
#                 self.payment,
#                 self.hire_booking,
#                 'hire',
#                 self.refund_request,
#                 self.mock_extract_stripe_refund_data.return_value
#             )

#     def test_handle_booking_refunded_zero_amount(self):
#         """
#         Tests that handle_booking_refunded returns early if refunded_amount_decimal is <= 0.
#         """
#         self.mock_extract_stripe_refund_data.return_value['refunded_amount_decimal'] = Decimal('0.00')
#         event_data = {'id': 'evt_test', 'object': 'event'}

#         with patch('django.db.transaction.atomic') as mock_atomic:
#             mock_atomic.return_value.__enter__.return_value = MagicMock()

#             handle_booking_refunded(self.payment, event_data)

#             self.mock_extract_stripe_refund_data.assert_called_once_with(event_data)
                                               
#             self.mock_get_booking_from_payment.assert_not_called()
#             self.mock_update_associated_bookings_and_payments.assert_not_called()
#             self.mock_process_refund_request_entry.assert_not_called()
#             self.mock_send_refund_notifications.assert_not_called()
#             mock_atomic.assert_called_once()                                    

#     def test_handle_booking_refunded_not_charge_or_refund_or_payment_intent_object(self):
#         """
#         Tests that handle_booking_refunded returns early if not a charge, refund, or payment intent object.
#         """
#         self.mock_extract_stripe_refund_data.return_value['is_charge_object'] = False
#         self.mock_extract_stripe_refund_data.return_value['is_refund_object'] = False
#         self.mock_extract_stripe_refund_data.return_value['is_payment_intent_object'] = False                            
#         event_data = {'id': 'evt_test', 'object': 'event'}

#         with patch('django.db.transaction.atomic') as mock_atomic:
#             mock_atomic.return_value.__enter__.return_value = MagicMock()

#             handle_booking_refunded(self.payment, event_data)

#             self.mock_extract_stripe_refund_data.assert_called_once_with(event_data)
                                               
#             self.mock_get_booking_from_payment.assert_not_called()
#             self.mock_update_associated_bookings_and_payments.assert_not_called()
#             self.mock_process_refund_request_entry.assert_not_called()
#             self.mock_send_refund_notifications.assert_not_called()
#             mock_atomic.assert_called_once()                                    

#     def test_handle_booking_refunded_exception_handling(self):
#         """
#         Tests that handle_booking_refunded re-raises exceptions.
#         """
#         event_data = {'id': 'evt_test', 'object': 'event'}
#         self.mock_extract_stripe_refund_data.side_effect = ValueError("Test Error")

#         with patch('django.db.transaction.atomic') as mock_atomic:
#             mock_atomic.return_value.__enter__.return_value = MagicMock()
            
#             with self.assertRaises(ValueError):
#                 handle_booking_refunded(self.payment, event_data)

#             self.mock_extract_stripe_refund_data.assert_called_once_with(event_data)
#             self.mock_get_booking_from_payment.assert_not_called()                                       
#             mock_atomic.assert_called_once()                                    

#     def test_handle_booking_refund_updated(self):
#         """
#         Tests that handle_booking_refund_updated calls handle_booking_refunded.
#         """
                                                                                          
#         with patch('payments.webhook_handlers.refund_handlers.handle_booking_refunded') as mock_handle_refunded_func:
#             event_data = {'id': 'evt_update', 'object': 'event'}
#             handle_booking_refund_updated(self.payment, event_data)
#             mock_handle_refunded_func.assert_called_once_with(self.payment, event_data)

#     def test_handle_booking_refunded_with_service_booking(self):
#         """
#         Tests the full flow of handle_booking_refunded for a valid refund (Service Booking).
#         """
                                                                                          
#         self.payment.service_booking = self.service_booking
#         self.payment.save()

#         self.mock_get_booking_from_payment.return_value = (self.service_booking, 'service')
#         event_data = {'id': 'evt_test_service', 'object': 'event'}

#         with patch('django.db.transaction.atomic') as mock_atomic:
#             mock_atomic.return_value.__enter__.return_value = MagicMock()

#             handle_booking_refunded(self.payment, event_data)

#             mock_atomic.assert_called_once()
#             self.mock_extract_stripe_refund_data.assert_called_once_with(event_data)
#             self.mock_get_booking_from_payment.assert_called_once_with(self.payment)
#             self.mock_update_associated_bookings_and_payments.assert_called_once_with(
#                 self.payment,
#                 self.service_booking,
#                 'service',
#                 Decimal('50.00')
#             )
#             self.mock_process_refund_request_entry.assert_called_once_with(
#                 self.payment,
#                 self.service_booking,
#                 'service',
#                 self.mock_extract_stripe_refund_data.return_value
#             )
#             self.mock_send_refund_notifications.assert_called_once_with(
#                 self.payment,
#                 self.service_booking,
#                 'service',
#                 self.refund_request,
#                 self.mock_extract_stripe_refund_data.return_value
#             )

#     def test_handle_booking_refunded_with_sales_booking(self):
#         """
#         Tests the full flow of handle_booking_refunded for a valid refund (Sales Booking).
#         """
                                                                                        
#         self.payment.sales_booking = self.sales_booking
#         self.payment.save()

#         self.mock_get_booking_from_payment.return_value = (self.sales_booking, 'sales')
#         event_data = {'id': 'evt_test_sales', 'object': 'event'}

#         with patch('django.db.transaction.atomic') as mock_atomic:
#             mock_atomic.return_value.__enter__.return_value = MagicMock()

#             handle_booking_refunded(self.payment, event_data)

#             mock_atomic.assert_called_once()
#             self.mock_extract_stripe_refund_data.assert_called_once_with(event_data)
#             self.mock_get_booking_from_payment.assert_called_once_with(self.payment)
#             self.mock_update_associated_bookings_and_payments.assert_called_once_with(
#                 self.payment,
#                 self.sales_booking,
#                 'sales',
#                 Decimal('50.00')
#             )
#             self.mock_process_refund_request_entry.assert_called_once_with(
#                 self.payment,
#                 self.sales_booking,
#                 'sales',
#                 self.mock_extract_stripe_refund_data.return_value
#             )
#             self.mock_send_refund_notifications.assert_called_once_with(
#                 self.payment,
#                 self.sales_booking,
#                 'sales',
#                 self.refund_request,
#                 self.mock_extract_stripe_refund_data.return_value
#             )

