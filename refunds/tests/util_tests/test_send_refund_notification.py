from django.test import TestCase
from unittest.mock import patch, MagicMock
from payments.utils.send_refund_notificiation import send_refund_notifications
from payments.tests.test_helpers.model_factories import PaymentFactory, SalesBookingFactory, ServiceBookingFactory, RefundRequestFactory, UserFactory, SalesProfileFactory, ServiceProfileFactory
from django.conf import settings
from decimal import Decimal

class SendRefundNotificationsTest(TestCase):

    def setUp(self):
        self.payment = PaymentFactory(amount=Decimal('100.00'), stripe_payment_intent_id='pi_test123')
        self.sales_profile = SalesProfileFactory(email='sales@example.com', name='Sales Customer', user__email='sales@example.com')
        self.service_profile = ServiceProfileFactory(email='service@example.com', name='Service Customer', user__email='service@example.com')
        self.sales_booking = SalesBookingFactory(sales_profile=self.sales_profile, payment=self.payment, sales_booking_reference='SALES-REF')
        self.service_booking = ServiceBookingFactory(service_profile=self.service_profile, payment=self.payment, service_booking_reference='SERVICE-REF')
        self.refund_request = RefundRequestFactory(reason='Test Reason', staff_notes='Test Staff Notes', is_admin_initiated=True)
        
        self._original_admin_email = getattr(settings, 'ADMIN_EMAIL', None)
        self._original_site_base_url = getattr(settings, 'SITE_BASE_URL', None)
        settings.ADMIN_EMAIL = 'admin@example.com'
        settings.SITE_BASE_URL = 'http://testserver'

    def tearDown(self):
        if self._original_admin_email is not None:
            settings.ADMIN_EMAIL = self._original_admin_email
        if self._original_site_base_url is not None:
            settings.SITE_BASE_URL = self._original_site_base_url

    # This test is failing because the SalesProfileFactory is generating a default email (e.g., user_X@example.com) 
    # even when email='sales@example.com' is passed to it. The factory's behavior is overriding the explicit email provided.
    @patch('payments.utils.send_refund_notificiation.send_templated_email')
    def test_send_sales_refund_notification(self, mock_send_templated_email):
        extracted_data = {
            'refunded_amount_decimal': Decimal('50.00'),
            'stripe_refund_id': 're_test123',
            'refund_status': 'succeeded',
            'is_refund_object': True,
        }
        send_refund_notifications(
            payment_obj=self.payment,
            booking_obj=self.sales_booking,
            booking_type_str='sales_booking',
            refund_request=self.refund_request,
            extracted_data=extracted_data,
        )

        self.assertEqual(mock_send_templated_email.call_count, 2)

        customer_call_args, customer_call_kwargs = mock_send_templated_email.call_args_list[0]
        self.assertEqual(customer_call_kwargs['recipient_list'], [self.sales_profile.email])
        self.assertIn('Your Refund for Booking SALES-REF Has Been Processed/Updated', customer_call_kwargs['subject'])
        self.assertEqual(customer_call_kwargs['template_name'], 'user_refund_processed_confirmation.html')
        self.assertEqual(customer_call_kwargs['context']['refunded_amount'], Decimal('50.00'))
        self.assertEqual(customer_call_kwargs['context']['booking_reference'], 'SALES-REF')
        self.assertEqual(customer_call_kwargs['context']['customer_name'], 'Sales Customer')
        self.assertEqual(customer_call_kwargs['context']['admin_message_from_refund'], self.refund_request.reason)
        self.assertEqual(customer_call_kwargs['booking'], self.sales_booking)
        self.assertEqual(customer_call_kwargs['sales_profile'], self.sales_profile)
        self.assertIsNone(customer_call_kwargs['service_profile'])

        admin_call_args, admin_call_kwargs = mock_send_templated_email.call_args_list[1]
        self.assertEqual(admin_call_kwargs['recipient_list'], [settings.ADMIN_EMAIL])
        self.assertIn('Stripe Refund Processed/Updated for Sales Booking SALES-REF', admin_call_kwargs['subject'])
        self.assertEqual(admin_call_kwargs['template_name'], 'admin_refund_processed_notification.html')
        self.assertEqual(admin_call_kwargs['context']['refunded_amount'], Decimal('50.00'))
        self.assertEqual(admin_call_kwargs['context']['stripe_refund_id'], 're_test123')
        self.assertEqual(admin_call_kwargs['context']['payment_id'], self.payment.id)
        self.assertEqual(admin_call_kwargs['context']['payment_intent_id'], 'pi_test123')
        self.assertEqual(admin_call_kwargs['context']['status'], 'succeeded')
        self.assertEqual(admin_call_kwargs['context']['event_type'], 'charge.refund.updated')
        self.assertEqual(admin_call_kwargs['context']['booking_type'], 'sales_booking')
        self.assertEqual(admin_call_kwargs['context']['customer_name'], 'Sales Customer')
        self.assertEqual(admin_call_kwargs['context']['refund_request_reason'], self.refund_request.reason)
        self.assertEqual(admin_call_kwargs['context']['refund_request_staff_notes'], self.refund_request.staff_notes)
        self.assertEqual(admin_call_kwargs['booking'], self.sales_booking)

    # This test is failing because the ServiceProfileFactory is generating a default email (e.g., user_Y@example.com) 
    # even when email='service@example.com' is passed to it. The factory's behavior is overriding the explicit email provided.
    @patch('payments.utils.send_refund_notificiation.send_templated_email')
    def test_send_service_refund_notification(self, mock_send_templated_email):
        extracted_data = {
            'refunded_amount_decimal': Decimal('75.00'),
            'stripe_refund_id': 're_test456',
            'refund_status': 'pending',
            'is_refund_object': False,
        }
        send_refund_notifications(
            payment_obj=self.payment,
            booking_obj=self.service_booking,
            booking_type_str='service_booking',
            refund_request=self.refund_request,
            extracted_data=extracted_data,
        )

        self.assertEqual(mock_send_templated_email.call_count, 2)

        customer_call_args, customer_call_kwargs = mock_send_templated_email.call_args_list[0]
        self.assertEqual(customer_call_kwargs['recipient_list'], [self.service_profile.email])
        self.assertIn('Your Refund for Booking SERVICE-REF Has Been Processed/Updated', customer_call_kwargs['subject'])
        self.assertEqual(customer_call_kwargs['template_name'], 'user_refund_processed_confirmation.html')
        self.assertEqual(customer_call_kwargs['context']['refunded_amount'], Decimal('75.00'))
        self.assertEqual(customer_call_kwargs['context']['booking_reference'], 'SERVICE-REF')
        self.assertEqual(customer_call_kwargs['context']['customer_name'], 'Service Customer')
        self.assertEqual(customer_call_kwargs['context']['admin_message_from_refund'], self.refund_request.reason)
        self.assertEqual(customer_call_kwargs['booking'], self.service_booking)
        self.assertEqual(customer_call_kwargs['service_profile'], self.service_profile)
        self.assertIsNone(customer_call_kwargs['sales_profile'])

        admin_call_args, admin_call_kwargs = mock_send_templated_email.call_args_list[1]
        self.assertEqual(admin_call_kwargs['recipient_list'], [settings.ADMIN_EMAIL])
        self.assertIn('Stripe Refund Processed/Updated for Service Booking SERVICE-REF', admin_call_kwargs['subject'])
        self.assertEqual(admin_call_kwargs['template_name'], 'admin_refund_processed_notification.html')
        self.assertEqual(admin_call_kwargs['context']['refunded_amount'], Decimal('75.00'))
        self.assertEqual(admin_call_kwargs['context']['stripe_refund_id'], 're_test456')
        self.assertEqual(admin_call_kwargs['context']['payment_id'], self.payment.id)
        self.assertEqual(admin_call_kwargs['context']['payment_intent_id'], 'pi_test123')
        self.assertEqual(admin_call_kwargs['context']['status'], 'pending')
        self.assertEqual(admin_call_kwargs['context']['event_type'], 'charge.refunded')
        self.assertEqual(admin_call_kwargs['context']['booking_type'], 'service_booking')
        self.assertEqual(admin_call_kwargs['context']['customer_name'], 'Service Customer')
        self.assertEqual(admin_call_kwargs['context']['refund_request_reason'], self.refund_request.reason)
        self.assertEqual(admin_call_kwargs['context']['refund_request_staff_notes'], self.refund_request.staff_notes)
        self.assertEqual(admin_call_kwargs['booking'], self.service_booking)

    @patch('payments.utils.send_refund_notificiation.send_templated_email')
    def test_send_refund_notification_no_booking_obj(self, mock_send_templated_email):
        extracted_data = {
            'refunded_amount_decimal': Decimal('10.00'),
            'stripe_refund_id': 're_test789',
            'refund_status': 'succeeded',
            'is_refund_object': True,
        }
        send_refund_notifications(
            payment_obj=self.payment,
            booking_obj=None,
            booking_type_str='unknown',
            refund_request=self.refund_request,
            extracted_data=extracted_data,
        )
        self.assertEqual(mock_send_templated_email.call_count, 1)
        admin_call_args, admin_call_kwargs = mock_send_templated_email.call_args_list[0]
        self.assertEqual(admin_call_kwargs['recipient_list'], [settings.ADMIN_EMAIL])
        self.assertIn('Stripe Refund Processed/Updated for Unknown N/A', admin_call_kwargs['subject'])

    # This test is failing because the send_refund_notifications function directly accesses settings.ADMIN_EMAIL 
    # without checking if it exists, and the test removes it.
    @patch('payments.utils.send_refund_notificiation.send_templated_email')
    def test_send_refund_notification_no_admin_email_setting(self, mock_send_templated_email):
        original_admin_email = getattr(settings, 'ADMIN_EMAIL', None)
        if hasattr(settings, 'ADMIN_EMAIL'):
            del settings.ADMIN_EMAIL

        extracted_data = {
            'refunded_amount_decimal': Decimal('10.00'),
            'stripe_refund_id': 're_test789',
            'refund_status': 'succeeded',
            'is_refund_object': True,
        }
        send_refund_notifications(
            payment_obj=self.payment,
            booking_obj=self.sales_booking,
            booking_type_str='sales_booking',
            refund_request=self.refund_request,
            extracted_data=extracted_data,
        )
        self.assertEqual(mock_send_templated_email.call_count, 1)
        customer_call_args, customer_call_kwargs = mock_send_templated_email.call_args_list[0]
        self.assertEqual(customer_call_kwargs['recipient_list'], [self.sales_profile.email])

        if original_admin_email is not None:
            settings.ADMIN_EMAIL = original_admin_email

    
