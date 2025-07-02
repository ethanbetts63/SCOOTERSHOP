import datetime
from decimal import Decimal
from unittest import mock

from django.test import TestCase
from datetime import timezone as dt_timezone                                        

                                          
from payments.utils.process_refund_request_entry import process_refund_request_entry

                                                       
from payments.tests.test_helpers.model_factories import (
    PaymentFactory,
    ServiceBookingFactory,
    RefundRequestFactory,
)


class ProcessRefundRequestEntryTestCase(TestCase):
    #--

    def setUp(self):
        #--
                                                                                               
                                                                
        self.mock_now = datetime.datetime(2023, 1, 15, 12, 0, 0, tzinfo=dt_timezone.utc)
        self.mock_now_patch = mock.patch('django.utils.timezone.now', return_value=self.mock_now)
        self.mock_now_patch.start()

    def tearDown(self):
        #--
        self.mock_now_patch.stop()


    def test_create_new_refund_request_for_service_booking(self):
        #--
        service_booking = ServiceBookingFactory()
        payment = PaymentFactory(service_booking=service_booking, status='succeeded')
        
        extracted_data = {
            'stripe_refund_id': 're_new_service_456',
            'refunded_amount_decimal': Decimal('75.00'),
        }

                                                                   
        self.assertEqual(service_booking.refund_requests.count(), 0)
        self.assertEqual(payment.refund_requests.count(), 0)


        refund_request = process_refund_request_entry(payment, service_booking, 'service_booking', extracted_data)

                                                        
        self.assertIsNotNone(refund_request)
        self.assertEqual(refund_request.payment, payment)
        self.assertEqual(refund_request.service_booking, service_booking)
        self.assertEqual(refund_request.stripe_refund_id, 're_new_service_456')
        self.assertEqual(refund_request.amount_to_refund, Decimal('75.00'))
        self.assertEqual(refund_request.status, 'partially_refunded')
        self.assertTrue(refund_request.is_admin_initiated)
        self.assertEqual(refund_request.processed_at, self.mock_now)
        self.assertIn("initial creation", refund_request.staff_notes)

                                             
        self.assertEqual(service_booking.refund_requests.count(), 1)
        self.assertEqual(payment.refund_requests.count(), 1)

    def test_update_existing_unverified_refund_request(self):
        #--
        service_booking = ServiceBookingFactory()
        payment = PaymentFactory(service_booking=service_booking, status='succeeded')
        
        existing_refund_request = RefundRequestFactory(
            payment=payment,
            service_booking=service_booking,
            status='unverified',
            amount_to_refund=Decimal('0.00'),
            stripe_refund_id=None,
            processed_at=None,
            staff_notes="Unverified user request.",
            requested_at=self.mock_now - datetime.timedelta(hours=5)
        )
        initial_notes = existing_refund_request.staff_notes

        extracted_data = {
            'stripe_refund_id': 're_updated_unverified_789',
            'refunded_amount_decimal': Decimal('120.00'),
        }

        updated_refund_request = process_refund_request_entry(payment, service_booking, 'service_booking', extracted_data)
        updated_refund_request.refresh_from_db()

        self.assertEqual(updated_refund_request.id, existing_refund_request.id)
        self.assertEqual(updated_refund_request.stripe_refund_id, 're_updated_unverified_789')
        self.assertEqual(updated_refund_request.amount_to_refund, Decimal('120.00'))
        self.assertEqual(updated_refund_request.status, 'partially_refunded')
        self.assertEqual(updated_refund_request.processed_at, self.mock_now)
        self.assertIn("updated existing request", updated_refund_request.staff_notes)
        self.assertTrue(updated_refund_request.staff_notes.startswith(initial_notes))


    def test_payment_status_is_refunded_for_existing_request(self):
        #--
        service_booking = ServiceBookingFactory()
                                               
        payment = PaymentFactory(service_booking=service_booking, status='refunded')
        
        existing_refund_request = RefundRequestFactory(
            payment=payment,
            service_booking=service_booking,
            status='pending',                            
            amount_to_refund=Decimal('0.00'),
        )

        extracted_data = {
            'stripe_refund_id': 're_full_refund_existing',
            'refunded_amount_decimal': Decimal('150.00'),
        }

        updated_refund_request = process_refund_request_entry(payment, service_booking, 'service_booking', extracted_data)
        updated_refund_request.refresh_from_db()

        self.assertEqual(updated_refund_request.status, 'refunded')
        self.assertEqual(updated_refund_request.amount_to_refund, Decimal('150.00'))


    def test_no_booking_linked_to_payment(self):
        #--
        payment = PaymentFactory(service_booking=None, status='succeeded')
        
        extracted_data = {
            'stripe_refund_id': 're_no_booking_linked',
            'refunded_amount_decimal': Decimal('25.00'),
        }

        refund_request = process_refund_request_entry(payment, None, 'unknown', extracted_data)

        self.assertIsNotNone(refund_request)
        self.assertEqual(refund_request.payment, payment)
        self.assertIsNone(refund_request.service_booking)
        self.assertEqual(refund_request.status, 'partially_refunded')                                                     
        self.assertIn("initial creation", refund_request.staff_notes)


