from django.test import TestCase
from unittest.mock import patch, MagicMock
from decimal import Decimal
from django.db import transaction

from payments.webhook_handlers.refund_handlers import handle_booking_refunded, handle_booking_refund_updated
from payments.tests.test_helpers.model_factories import PaymentFactory, RefundRequestFactory, ServiceBookingFactory, SalesBookingFactory

class RefundHandlersTest(TestCase):

    def setUp(self):
        self.payment = PaymentFactory()
        self.service_booking = ServiceBookingFactory()
        self.sales_booking = SalesBookingFactory()
        self.refund_request = RefundRequestFactory()
        self.event_object_data = {
            'object': 'charge',
            'id': 'ch_test',
            'amount_refunded': 5000,
            'refunds': {'data': [{'id': 're_test', 'status': 'succeeded', 'amount': 5000}]}
        }
        self.extracted_data = {
            'refunded_amount_decimal': Decimal('50.00'),
            'is_charge_object': True,
            'is_refund_object': False,
            'is_payment_intent_object': False,
            'stripe_refund_id': 're_test',
            'refund_status': 'succeeded',
        }

    @patch('payments.webhook_handlers.refund_handlers.send_refund_notifications')
    @patch('payments.webhook_handlers.refund_handlers.process_refund_request_entry')
    @patch('payments.webhook_handlers.refund_handlers.update_associated_bookings_and_payments')
    @patch('payments.webhook_handlers.refund_handlers.get_booking_from_payment')
    @patch('payments.webhook_handlers.refund_handlers.extract_stripe_refund_data')
    def test_handle_booking_refunded_successful_full_refund(self, mock_extract_stripe_refund_data, mock_get_booking_from_payment, mock_update_associated_bookings_and_payments, mock_process_refund_request_entry, mock_send_refund_notifications):
        mock_extract_stripe_refund_data.return_value = self.extracted_data
        mock_get_booking_from_payment.return_value = (self.service_booking, 'service_booking')
        mock_process_refund_request_entry.return_value = self.refund_request

        handle_booking_refunded(self.payment, self.event_object_data)

        mock_extract_stripe_refund_data.assert_called_once_with(self.event_object_data)
        mock_get_booking_from_payment.assert_called_once_with(self.payment)
        mock_update_associated_bookings_and_payments.assert_called_once_with(
            self.payment,
            self.service_booking,
            'service_booking',
            self.extracted_data['refunded_amount_decimal']
        )
        mock_process_refund_request_entry.assert_called_once_with(
            self.payment,
            self.service_booking,
            'service_booking',
            self.extracted_data
        )
        mock_send_refund_notifications.assert_called_once_with(
            self.payment,
            self.service_booking,
            'service_booking',
            self.refund_request,
            self.extracted_data
        )

    @patch('payments.webhook_handlers.refund_handlers.send_refund_notifications')
    @patch('payments.webhook_handlers.refund_handlers.process_refund_request_entry')
    @patch('payments.webhook_handlers.refund_handlers.update_associated_bookings_and_payments')
    @patch('payments.webhook_handlers.refund_handlers.get_booking_from_payment')
    @patch('payments.webhook_handlers.refund_handlers.extract_stripe_refund_data')
    def test_handle_booking_refunded_refunded_amount_is_zero(self, mock_extract_stripe_refund_data, mock_get_booking_from_payment, mock_update_associated_bookings_and_payments, mock_process_refund_request_entry, mock_send_refund_notifications):
        self.extracted_data['refunded_amount_decimal'] = Decimal('0.00')
        mock_extract_stripe_refund_data.return_value = self.extracted_data

        handle_booking_refunded(self.payment, self.event_object_data)

        mock_extract_stripe_refund_data.assert_called_once_with(self.event_object_data)
        mock_get_booking_from_payment.assert_not_called()
        mock_update_associated_bookings_and_payments.assert_not_called()
        mock_process_refund_request_entry.assert_not_called()
        mock_send_refund_notifications.assert_not_called()

    @patch('payments.webhook_handlers.refund_handlers.send_refund_notifications')
    @patch('payments.webhook_handlers.refund_handlers.process_refund_request_entry')
    @patch('payments.webhook_handlers.refund_handlers.update_associated_bookings_and_payments')
    @patch('payments.webhook_handlers.refund_handlers.get_booking_from_payment')
    @patch('payments.webhook_handlers.refund_handlers.extract_stripe_refund_data')
    def test_handle_booking_refunded_invalid_stripe_object_type(self, mock_extract_stripe_refund_data, mock_get_booking_from_payment, mock_update_associated_bookings_and_payments, mock_process_refund_request_entry, mock_send_refund_notifications):
        self.extracted_data['is_charge_object'] = False
        self.extracted_data['is_refund_object'] = False
        self.extracted_data['is_payment_intent_object'] = False
        mock_extract_stripe_refund_data.return_value = self.extracted_data

        handle_booking_refunded(self.payment, self.event_object_data)

        mock_extract_stripe_refund_data.assert_called_once_with(self.event_object_data)
        mock_get_booking_from_payment.assert_not_called()
        mock_update_associated_bookings_and_payments.assert_not_called()
        mock_process_refund_request_entry.assert_not_called()
        mock_send_refund_notifications.assert_not_called()

    @patch('payments.webhook_handlers.refund_handlers.extract_stripe_refund_data', side_effect=Exception("Test Exception"))
    def test_handle_booking_refunded_exception_handling(self, mock_extract_stripe_refund_data):
        with self.assertRaises(Exception) as cm:
            handle_booking_refunded(self.payment, self.event_object_data)
        self.assertEqual(str(cm.exception), "Test Exception")

    @patch('payments.webhook_handlers.refund_handlers.handle_booking_refunded')
    def test_handle_booking_refund_updated_calls_handle_booking_refunded(self, mock_handle_booking_refunded):
        handle_booking_refund_updated(self.payment, self.event_object_data)
        mock_handle_booking_refunded.assert_called_once_with(self.payment, self.event_object_data)