from decimal import Decimal
from unittest import mock

from django.test import TestCase, override_settings

from payments.utils.send_refund_notificiation import send_refund_notifications

from payments.tests.test_helpers.model_factories import (
    PaymentFactory,
    HireBookingFactory,
    ServiceBookingFactory,
    RefundRequestFactory,
    DriverProfileFactory,
    ServiceProfileFactory,
    UserFactory,
    SalesBookingFactory,
    SalesProfileFactory,
)


@override_settings(
    ADMIN_EMAIL='admin@example.com',
    DEFAULT_FROM_EMAIL='noreply@example.com',
    SITE_BASE_URL='http://test.com',
)
class SendRefundNotificationsTestCase(TestCase):
    @mock.patch('payments.utils.send_refund_notificiation.send_templated_email')
    def test_send_notifications_for_hire_booking_with_user_email(self, mock_send_templated_email):
        user = UserFactory(email='testuser@example.com')
        driver_profile = DriverProfileFactory(user=user)
        hire_booking = HireBookingFactory(driver_profile=driver_profile)
        payment = PaymentFactory(
            hire_booking=hire_booking,
            service_booking=None,
            stripe_payment_intent_id='pi_hire_123',
            amount=Decimal('200.00'),
            status='succeeded'
        )
        refund_request = RefundRequestFactory(
            payment=payment,
            hire_booking=hire_booking,
            amount_to_refund=Decimal('50.00'),
            status='partially_refunded',
            stripe_refund_id='re_hire_123'
        )
        extracted_data = {
            'refunded_amount_decimal': Decimal('50.00'),
            'stripe_refund_id': 're_hire_123',
            'refund_status': 'succeeded',
            'is_refund_object': False,
        }

        send_refund_notifications(payment, hire_booking, 'hire_booking', refund_request, extracted_data)

        self.assertEqual(mock_send_templated_email.call_count, 2)

        user_call_args, user_call_kwargs = mock_send_templated_email.call_args_list[0]
        self.assertEqual(user_call_kwargs['recipient_list'], [user.email])
        self.assertIn(f"Your Refund for Booking {hire_booking.booking_reference} Has Been Processed/Updated", user_call_kwargs['subject'])
        self.assertEqual(user_call_kwargs['template_name'], 'user_refund_processed_confirmation.html')
        self.assertEqual(user_call_kwargs['booking'], hire_booking)
        self.assertEqual(user_call_kwargs['driver_profile'], driver_profile)
        self.assertIsNone(user_call_kwargs['service_profile'])
        self.assertEqual(user_call_kwargs['context']['refunded_amount'], Decimal('50.00'))
        self.assertEqual(user_call_kwargs['context']['booking_reference'], hire_booking.booking_reference)
        self.assertEqual(user_call_kwargs['context']['customer_name'], driver_profile.name)
        self.assertEqual(user_call_kwargs['context']['refund_policy_link'], 'http://test.com/returns/')
        self.assertEqual(user_call_kwargs['context']['admin_email'], 'admin@example.com')


        admin_call_args, admin_call_kwargs = mock_send_templated_email.call_args_list[1]
        self.assertEqual(admin_call_kwargs['recipient_list'], ['admin@example.com'])
        self.assertIn(f"Stripe Refund Processed/Updated for Hire Booking {hire_booking.booking_reference}", admin_call_kwargs['subject'])
        self.assertEqual(admin_call_kwargs['template_name'], 'admin_refund_processed_notification.html')
        self.assertEqual(admin_call_kwargs['booking'], hire_booking)
        self.assertEqual(admin_call_kwargs['context']['refunded_amount'], Decimal('50.00'))
        self.assertEqual(admin_call_kwargs['context']['stripe_refund_id'], 're_hire_123')
        self.assertEqual(admin_call_kwargs['context']['payment_id'], payment.id)
        self.assertEqual(admin_call_kwargs['context']['payment_intent_id'], payment.stripe_payment_intent_id)
        self.assertEqual(admin_call_kwargs['context']['status'], 'succeeded')
        self.assertEqual(admin_call_kwargs['context']['event_type'], 'charge.refunded')
        self.assertEqual(admin_call_kwargs['context']['booking_type'], 'hire_booking')
        self.assertEqual(admin_call_kwargs['context']['customer_name'], driver_profile.name)


    @mock.patch('payments.utils.send_refund_notificiation.send_templated_email')
    def test_send_notifications_for_service_booking_with_user_email(self, mock_send_templated_email):
        user = UserFactory(email='services_user@example.com')
        service_profile = ServiceProfileFactory(user=user, email='services_user@example.com')
        service_booking = ServiceBookingFactory(service_profile=service_profile)
        payment = PaymentFactory(
            service_booking=service_booking,
            hire_booking=None,
            stripe_payment_intent_id='pi_service_456',
            amount=Decimal('300.00'),
            status='succeeded'
        )
        refund_request = RefundRequestFactory(
            payment=payment,
            service_booking=service_booking,
            amount_to_refund=Decimal('75.00'),
            status='partially_refunded',
            stripe_refund_id='re_service_456'
        )
        extracted_data = {
            'refunded_amount_decimal': Decimal('75.00'),
            'stripe_refund_id': 're_service_456',
            'refund_status': 'succeeded',
            'is_refund_object': True,
        }

        send_refund_notifications(payment, service_booking, 'service_booking', refund_request, extracted_data)

        self.assertEqual(mock_send_templated_email.call_count, 2)

        user_call_args, user_call_kwargs = mock_send_templated_email.call_args_list[0]
        self.assertEqual(user_call_kwargs['recipient_list'], [user.email])
        self.assertIn(f"Your Refund for Booking {service_booking.service_booking_reference} Has Been Processed/Updated", user_call_kwargs['subject'])
        self.assertEqual(user_call_kwargs['template_name'], 'user_refund_processed_confirmation.html')
        self.assertEqual(user_call_kwargs['booking'], service_booking)
        self.assertIsNone(user_call_kwargs['driver_profile'])
        self.assertEqual(user_call_kwargs['service_profile'], service_profile)
        self.assertEqual(user_call_kwargs['context']['customer_name'], service_profile.name)
        self.assertEqual(user_call_kwargs['context']['admin_email'], 'admin@example.com')


        admin_call_args, admin_call_kwargs = mock_send_templated_email.call_args_list[1]
        self.assertEqual(admin_call_kwargs['recipient_list'], ['admin@example.com'])
        self.assertIn(f"Stripe Refund Processed/Updated for Service Booking {service_booking.service_booking_reference}", admin_call_kwargs['subject'])
        self.assertEqual(admin_call_kwargs['context']['event_type'], 'charge.refund.updated')
        self.assertEqual(admin_call_kwargs['context']['customer_name'], service_profile.name)


    @mock.patch('payments.utils.send_refund_notificiation.send_templated_email')
    def test_send_notifications_for_service_booking_no_user_object_email_from_profile(self, mock_send_templated_email):
        service_profile = ServiceProfileFactory(user=None, email='anon_service@example.com')
        service_booking = ServiceBookingFactory(service_profile=service_profile)
        payment = PaymentFactory(
            service_booking=service_booking,
            hire_booking=None,
            stripe_payment_intent_id='pi_service_789',
            amount=Decimal('100.00'),
            status='succeeded'
        )
        refund_request = RefundRequestFactory(
            payment=payment,
            service_booking=service_booking,
            amount_to_refund=Decimal('20.00'),
            status='partially_refunded',
            stripe_refund_id='re_service_789'
        )
        extracted_data = {
            'refunded_amount_decimal': Decimal('20.00'),
            'stripe_refund_id': 're_service_789',
            'refund_status': 'succeeded',
            'is_refund_object': False,
        }

        send_refund_notifications(payment, service_booking, 'service_booking', refund_request, extracted_data)

        self.assertEqual(mock_send_templated_email.call_count, 2)

        user_call_args, user_call_kwargs = mock_send_templated_email.call_args_list[0]
        self.assertEqual(user_call_kwargs['recipient_list'], [service_profile.email])
        self.assertEqual(user_call_kwargs['context']['customer_name'], service_profile.name)
        self.assertEqual(user_call_kwargs['context']['admin_email'], 'admin@example.com')


    @mock.patch('payments.utils.send_refund_notificiation.send_templated_email')
    def test_send_notifications_no_user_email_only_admin_sent(self, mock_send_templated_email):
        driver_profile = DriverProfileFactory(user=None, email='dummy_email_for_non_user@example.com') 
        hire_booking = HireBookingFactory(driver_profile=driver_profile)
        payment = PaymentFactory(
            hire_booking=hire_booking,
            service_booking=None,
            stripe_payment_intent_id='pi_no_user_email',
            amount=Decimal('100.00'),
            status='succeeded'
        )
        refund_request = RefundRequestFactory(
            payment=payment,
            hire_booking=hire_booking,
            amount_to_refund=Decimal('25.00'),
            status='partially_refunded',
            stripe_refund_id='re_no_user_email'
        )
        extracted_data = {
            'refunded_amount_decimal': Decimal('25.00'),
            'stripe_refund_id': 're_no_user_email',
            'refund_status': 'succeeded',
            'is_refund_object': False,
        }

        send_refund_notifications(payment, hire_booking, 'hire_booking', refund_request, extracted_data)

        self.assertEqual(mock_send_templated_email.call_count, 1)

        admin_call_args, admin_call_kwargs = mock_send_templated_email.call_args_list[0]
        self.assertEqual(admin_call_kwargs['recipient_list'], ['admin@example.com'])
        self.assertIn("Stripe Refund Processed/Updated for Hire Booking", admin_call_kwargs['subject'])
        self.assertEqual(admin_call_kwargs['context']['customer_name'], driver_profile.name)


    @mock.patch('payments.utils.send_refund_notificiation.send_templated_email')
    @override_settings(ADMIN_EMAIL=None)
    def test_no_admin_email_only_user_sent_if_available(self, mock_send_templated_email):
        user = UserFactory(email='user_only@example.com')
        driver_profile = DriverProfileFactory(user=user)
        hire_booking = HireBookingFactory(driver_profile=driver_profile)
        payment = PaymentFactory(
            hire_booking=hire_booking,
            service_booking=None,
            stripe_payment_intent_id='pi_user_only',
            amount=Decimal('100.00'),
            status='succeeded'
        )
        refund_request = RefundRequestFactory(
            payment=payment,
            hire_booking=hire_booking,
            amount_to_refund=Decimal('25.00'),
            status='partially_refunded',
            stripe_refund_id='re_user_only'
        )
        extracted_data = {
            'refunded_amount_decimal': Decimal('25.00'),
            'stripe_refund_id': 're_user_only',
            'refund_status': 'succeeded',
            'is_refund_object': False,
        }

        send_refund_notifications(payment, hire_booking, 'hire_booking', refund_request, extracted_data)

        self.assertEqual(mock_send_templated_email.call_count, 1)

        user_call_args, user_call_kwargs = mock_send_templated_email.call_args_list[0]
        self.assertEqual(user_call_kwargs['recipient_list'], [user.email])
        self.assertIn('/returns/', user_call_kwargs['context']['refund_policy_link'])
        self.assertIsNone(user_call_kwargs['context']['admin_email'])


    @mock.patch('payments.utils.send_refund_notificiation.send_templated_email')
    def test_send_notifications_with_is_refund_object_true(self, mock_send_templated_email):
        user = UserFactory(email='testuser@example.com')
        driver_profile = DriverProfileFactory(user=user)
        hire_booking = HireBookingFactory(driver_profile=driver_profile)
        payment = PaymentFactory(
            hire_booking=hire_booking,
            service_booking=None,
            stripe_payment_intent_id='pi_refund_obj_true',
            amount=Decimal('200.00'),
            status='succeeded'
        )
        refund_request = RefundRequestFactory(
            payment=payment,
            hire_booking=hire_booking,
            amount_to_refund=Decimal('50.00'),
            status='partially_refunded',
            stripe_refund_id='re_refund_obj_true'
        )
        extracted_data = {
            'refunded_amount_decimal': Decimal('50.00'),
            'stripe_refund_id': 're_refund_obj_true',
            'refund_status': 'succeeded',
            'is_refund_object': True,
        }

        send_refund_notifications(payment, hire_booking, 'hire_booking', refund_request, extracted_data)

        self.assertEqual(mock_send_templated_email.call_count, 2)
        admin_call_args, admin_call_kwargs = mock_send_templated_email.call_args_list[1]
        self.assertEqual(admin_call_kwargs['context']['event_type'], 'charge.refund.updated')
        self.assertEqual(admin_call_kwargs['context']['customer_name'], driver_profile.name)

    @mock.patch('payments.utils.send_refund_notificiation.send_templated_email')
    def test_send_notifications_with_is_refund_object_false(self, mock_send_templated_email):
        user = UserFactory(email='testuser@example.com')
        driver_profile = DriverProfileFactory(user=user)
        hire_booking = HireBookingFactory(driver_profile=driver_profile)
        payment = PaymentFactory(
            hire_booking=hire_booking,
            service_booking=None,
            stripe_payment_intent_id='pi_refund_obj_false',
            amount=Decimal('200.00'),
            status='succeeded'
        )
        refund_request = RefundRequestFactory(
            payment=payment,
            hire_booking=hire_booking,
            amount_to_refund=Decimal('50.00'),
            status='partially_refunded',
            stripe_refund_id='re_refund_obj_false'
        )
        extracted_data = {
            'refunded_amount_decimal': Decimal('50.00'),
            'stripe_refund_id': 're_refund_obj_false',
            'refund_status': 'succeeded',
            'is_refund_object': False,
        }

        send_refund_notifications(payment, hire_booking, 'hire_booking', refund_request, extracted_data)

        self.assertEqual(mock_send_templated_email.call_count, 2)
        admin_call_args, admin_call_kwargs = mock_send_templated_email.call_args_list[1]
        self.assertEqual(admin_call_kwargs['context']['event_type'], 'charge.refunded')
        self.assertEqual(admin_call_kwargs['context']['customer_name'], driver_profile.name)

    @mock.patch('payments.utils.send_refund_notificiation.send_templated_email')
    @override_settings(ADMIN_EMAIL=None, SITE_BASE_URL='http://example.com')
    def test_send_notifications_no_admin_or_site_base_url(self, mock_send_templated_email):
        user = UserFactory(email='user_only@example.com')
        driver_profile = DriverProfileFactory(user=user)
        hire_booking = HireBookingFactory(driver_profile=driver_profile)
        payment = PaymentFactory(
            hire_booking=hire_booking,
            service_booking=None,
            stripe_payment_intent_id='pi_user_only_no_admin',
            amount=Decimal('100.00'),
            status='succeeded'
        )
        refund_request = RefundRequestFactory(
            payment=payment,
            hire_booking=hire_booking,
            amount_to_refund=Decimal('25.00'),
            status='partially_refunded',
            stripe_refund_id='re_user_only_no_admin'
        )
        extracted_data = {
            'refunded_amount_decimal': Decimal('25.00'),
            'stripe_refund_id': 're_user_only_no_admin',
            'refund_status': 'succeeded',
            'is_refund_object': False,
        }

        send_refund_notifications(payment, hire_booking, 'hire_booking', refund_request, extracted_data)

        self.assertEqual(mock_send_templated_email.call_count, 1)
        user_call_args, user_call_kwargs = mock_send_templated_email.call_args_list[0]
        self.assertEqual(user_call_kwargs['recipient_list'], [user.email])
        self.assertIn('/returns/', user_call_kwargs['context']['refund_policy_link'])
        self.assertIsNone(user_call_kwargs['context']['admin_email'])

    @mock.patch('payments.utils.send_refund_notificiation.send_templated_email')
    def test_send_notifications_for_sales_booking_with_user_email(self, mock_send_templated_email):
        user = UserFactory(email='sales_user@example.com')
        sales_profile = SalesProfileFactory(user=user, email='sales_user@example.com')
        sales_booking = SalesBookingFactory(sales_profile=sales_profile)
        payment = PaymentFactory(
            sales_booking=sales_booking,
            hire_booking=None,
            service_booking=None,
            stripe_payment_intent_id='pi_sales_123',
            amount=Decimal('500.00'),
            status='succeeded'
        )
        refund_request = RefundRequestFactory(
            payment=payment,
            sales_booking=sales_booking,
            amount_to_refund=Decimal('100.00'),
            status='partially_refunded',
            stripe_refund_id='re_sales_123'
        )
        extracted_data = {
            'refunded_amount_decimal': Decimal('100.00'),
            'stripe_refund_id': 're_sales_123',
            'refund_status': 'succeeded',
            'is_refund_object': False,
        }

        send_refund_notifications(payment, sales_booking, 'sales_booking', refund_request, extracted_data)

        self.assertEqual(mock_send_templated_email.call_count, 2)

        user_call_args, user_call_kwargs = mock_send_templated_email.call_args_list[0]
        self.assertEqual(user_call_kwargs['recipient_list'], [user.email])
        self.assertIn(f"Your Refund for Booking {sales_booking.sales_booking_reference} Has Been Processed/Updated", user_call_kwargs['subject'])
        self.assertEqual(user_call_kwargs['template_name'], 'user_refund_processed_confirmation.html')
        self.assertEqual(user_call_kwargs['booking'], sales_booking)
        self.assertIsNone(user_call_kwargs['driver_profile'])
        self.assertIsNone(user_call_kwargs['service_profile'])
        self.assertEqual(user_call_kwargs['sales_profile'], sales_profile)
        self.assertEqual(user_call_kwargs['context']['refunded_amount'], Decimal('100.00'))
        self.assertEqual(user_call_kwargs['context']['booking_reference'], sales_booking.sales_booking_reference)
        self.assertEqual(user_call_kwargs['context']['customer_name'], sales_profile.name)
        self.assertEqual(user_call_kwargs['context']['refund_policy_link'], 'http://test.com/returns/')
        self.assertEqual(user_call_kwargs['context']['admin_email'], 'admin@example.com')

        admin_call_args, admin_call_kwargs = mock_send_templated_email.call_args_list[1]
        self.assertEqual(admin_call_kwargs['recipient_list'], ['admin@example.com'])
        self.assertIn(f"Stripe Refund Processed/Updated for Sales Booking {sales_booking.sales_booking_reference}", admin_call_kwargs['subject'])
        self.assertEqual(admin_call_kwargs['template_name'], 'admin_refund_processed_notification.html')
        self.assertEqual(admin_call_kwargs['booking'], sales_booking)
        self.assertEqual(admin_call_kwargs['context']['refunded_amount'], Decimal('100.00'))
        self.assertEqual(admin_call_kwargs['context']['stripe_refund_id'], 're_sales_123')
        self.assertEqual(admin_call_kwargs['context']['payment_id'], payment.id)
        self.assertEqual(admin_call_kwargs['context']['payment_intent_id'], payment.stripe_payment_intent_id)
        self.assertEqual(admin_call_kwargs['context']['status'], 'succeeded')
        self.assertEqual(admin_call_kwargs['context']['event_type'], 'charge.refunded')
        self.assertEqual(admin_call_kwargs['context']['booking_type'], 'sales_booking')
        self.assertEqual(admin_call_kwargs['context']['customer_name'], sales_profile.name)
