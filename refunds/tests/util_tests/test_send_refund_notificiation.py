from django.test import TestCase, override_settings
from django.urls import reverse
from unittest import mock
from decimal import Decimal
from django.conf import settings
from refunds.utils.send_refund_notification import send_refund_notifications
from payments.models import Payment
from refunds.models import RefundRequest
from service.models import ServiceBooking, ServiceProfile
from inventory.models import SalesBooking, SalesProfile
from users.tests.test_helpers.model_factories import UserFactory
from service.tests.test_helpers.model_factories import ServiceBookingFactory, ServiceProfileFactory
from inventory.tests.test_helpers.model_factories import SalesBookingFactory, SalesProfileFactory
from payments.tests.test_helpers.model_factories import PaymentFactory
from refunds.tests.test_helpers.model_factories import RefundRequestFactory

@override_settings(
    ADMIN_EMAIL="admin@example.com",
    DEFAULT_FROM_EMAIL="default@example.com",
    SITE_BASE_URL="http://testserver",
)
class SendRefundNotificationsTest(TestCase):

    def setUp(self):
        # Ensure clean state for models
        ServiceBooking.objects.all().delete()
        SalesBooking.objects.all().delete()
        Payment.objects.all().delete()
        RefundRequest.objects.all().delete()
        ServiceProfile.objects.all().delete()
        SalesProfile.objects.all().delete()

        # Create a user for profiles
        self.user = UserFactory(email="user@example.com")

        # Common extracted data for tests
        self.extracted_data = {
            "refunded_amount_decimal": Decimal("50.00"),
            "stripe_refund_id": "re_test_id",
            "refund_status": "succeeded",
            "is_refund_object": False,
        }

    @mock.patch('refunds.utils.send_refund_notification.send_templated_email')
    def test_service_booking_refund_notification_user_email(self, mock_send_templated_email):
        service_profile = ServiceProfileFactory(user=self.user, email="") # Ensure email comes from user
        booking = ServiceBookingFactory(service_profile=service_profile, amount_paid=Decimal("100.00"))
        payment = PaymentFactory(service_booking=booking, amount=Decimal("100.00"))
        refund_request = RefundRequestFactory(payment=payment, service_booking=booking, reason="Test reason")

        send_refund_notifications(payment, booking, "service_booking", refund_request, self.extracted_data)

        # Assert user email was sent
        mock_send_templated_email.assert_any_call(
            recipient_list=[self.user.email],
            subject=f"Your Refund for Booking {booking.service_booking_reference} Has Been Processed/Updated",
            template_name="user_refund_processed_confirmation.html",
            context=mock.ANY,
            booking=booking,
            profile=service_profile,
        )
        # Verify context for user email
        args, kwargs = mock_send_templated_email.call_args_list[0]
        self.assertEqual(kwargs['context']['refunded_amount'], self.extracted_data['refunded_amount_decimal'])
        self.assertEqual(kwargs['context']['booking_reference'], booking.service_booking_reference)
        self.assertEqual(kwargs['context']['customer_name'], service_profile.name)
        self.assertIn(settings.SITE_BASE_URL + "/returns/", kwargs['context']['refund_policy_link'])

    @mock.patch('refunds.utils.send_refund_notification.send_templated_email')
    def test_sales_booking_refund_notification_user_email(self, mock_send_templated_email):
        sales_profile = SalesProfileFactory(user=self.user, email="") # Ensure email comes from user
        booking = SalesBookingFactory(sales_profile=sales_profile, amount_paid=Decimal("100.00"))
        payment = PaymentFactory(sales_booking=booking, amount=Decimal("100.00"))
        refund_request = RefundRequestFactory(payment=payment, sales_booking=booking, reason="Test reason")

        send_refund_notifications(payment, booking, "sales_booking", refund_request, self.extracted_data)

        # Assert user email was sent
        mock_send_templated_email.assert_any_call(
            recipient_list=[self.user.email],
            subject=f"Your Refund for Booking {booking.sales_booking_reference} Has Been Processed/Updated",
            template_name="user_refund_processed_confirmation.html",
            context=mock.ANY,
            booking=booking,
            profile=sales_profile,
        )
        # Verify context for user email
        args, kwargs = mock_send_templated_email.call_args_list[0]
        self.assertEqual(kwargs['context']['refunded_amount'], self.extracted_data['refunded_amount_decimal'])
        self.assertEqual(kwargs['context']['booking_reference'], booking.sales_booking_reference)
        self.assertEqual(kwargs['context']['customer_name'], sales_profile.name)

    @mock.patch('refunds.utils.send_refund_notification.send_templated_email')
    def test_service_booking_refund_notification_profile_email_no_user(self, mock_send_templated_email):
        service_profile = ServiceProfileFactory(user=None, email="profile@example.com")
        booking = ServiceBookingFactory(service_profile=service_profile, amount_paid=Decimal("100.00"))
        payment = PaymentFactory(service_booking=booking, amount=Decimal("100.00"))
        refund_request = RefundRequestFactory(payment=payment, service_booking=booking, reason="Test reason")

        send_refund_notifications(payment, booking, "service_booking", refund_request, self.extracted_data)

        # Assert user email was sent to profile email
        mock_send_templated_email.assert_any_call(
            recipient_list=[service_profile.email],
            subject=mock.ANY,
            template_name=mock.ANY,
            context=mock.ANY,
            booking=mock.ANY,
            profile=service_profile,
        )

    @mock.patch('refunds.utils.send_refund_notification.send_templated_email')
    def test_sales_booking_refund_notification_profile_email_no_user(self, mock_send_templated_email):
        sales_profile = SalesProfileFactory(user=None, email="profile@example.com")
        booking = SalesBookingFactory(sales_profile=sales_profile, amount_paid=Decimal("100.00"))
        payment = PaymentFactory(sales_booking=booking, amount=Decimal("100.00"))
        refund_request = RefundRequestFactory(payment=payment, sales_booking=booking, reason="Test reason")

        send_refund_notifications(payment, booking, "sales_booking", refund_request, self.extracted_data)

        # Assert user email was sent to profile email
        mock_send_templated_email.assert_any_call(
            recipient_list=[sales_profile.email],
            subject=mock.ANY,
            template_name=mock.ANY,
            context=mock.ANY,
            booking=mock.ANY,
            profile=sales_profile,
        )

    @mock.patch('refunds.utils.send_refund_notification.send_templated_email')
    def test_admin_notification_service_booking(self, mock_send_templated_email):
        service_profile = ServiceProfileFactory(user=self.user)
        booking = ServiceBookingFactory(service_profile=service_profile, amount_paid=Decimal("100.00"))
        payment = PaymentFactory(service_booking=booking, amount=Decimal("100.00"))
        refund_request = RefundRequestFactory(payment=payment, service_booking=booking, reason="Test reason")

        send_refund_notifications(payment, booking, "service_booking", refund_request, self.extracted_data)

        # Assert admin email was sent
        mock_send_templated_email.assert_any_call(
            recipient_list=[settings.ADMIN_EMAIL],
            subject=mock.ANY,
            template_name="admin_refund_processed_notification.html",
            context=mock.ANY,
            booking=booking,
            profile=None,
        )
        # Verify context for admin email
        args, kwargs = mock_send_templated_email.call_args_list[1] # Admin email is the second call
        self.assertEqual(kwargs['context']['refunded_amount'], self.extracted_data['refunded_amount_decimal'])
        self.assertEqual(kwargs['context']['booking_reference'], booking.service_booking_reference)
        self.assertEqual(kwargs['context']['stripe_refund_id'], self.extracted_data['stripe_refund_id'])
        self.assertEqual(kwargs['context']['payment_id'], payment.id)
        self.assertEqual(kwargs['context']['payment_intent_id'], payment.stripe_payment_intent_id)
        self.assertEqual(kwargs['context']['status'], self.extracted_data['refund_status'])
        self.assertEqual(kwargs['context']['event_type'], "charge.refunded")
        self.assertEqual(kwargs['context']['booking_type'], "service_booking")
        self.assertEqual(kwargs['context']['customer_name'], service_profile.name)
        self.assertEqual(kwargs['context']['refund_request_reason'], refund_request.reason)

    @mock.patch('refunds.utils.send_refund_notification.send_templated_email')
    def test_admin_notification_sales_booking(self, mock_send_templated_email):
        sales_profile = SalesProfileFactory(user=self.user)
        booking = SalesBookingFactory(sales_profile=sales_profile, amount_paid=Decimal("100.00"))
        payment = PaymentFactory(sales_booking=booking, amount=Decimal("100.00"))
        refund_request = RefundRequestFactory(payment=payment, sales_booking=booking, reason="Test reason")

        send_refund_notifications(payment, booking, "sales_booking", refund_request, self.extracted_data)

        # Assert admin email was sent
        mock_send_templated_email.assert_any_call(
            recipient_list=[settings.ADMIN_EMAIL],
            subject=mock.ANY,
            template_name="admin_refund_processed_notification.html",
            context=mock.ANY,
            booking=booking,
            profile=None,
        )
        # Verify context for admin email
        args, kwargs = mock_send_templated_email.call_args_list[1] # Admin email is the second call
        self.assertEqual(kwargs['context']['refunded_amount'], self.extracted_data['refunded_amount_decimal'])
        self.assertEqual(kwargs['context']['booking_reference'], booking.sales_booking_reference)
        self.assertEqual(kwargs['context']['stripe_refund_id'], self.extracted_data['stripe_refund_id'])
        self.assertEqual(kwargs['context']['payment_id'], payment.id)
        self.assertEqual(kwargs['context']['payment_intent_id'], payment.stripe_payment_intent_id)
        self.assertEqual(kwargs['context']['status'], self.extracted_data['refund_status'])
        self.assertEqual(kwargs['context']['event_type'], "charge.refunded")
        self.assertEqual(kwargs['context']['booking_type'], "sales_booking")
        self.assertEqual(kwargs['context']['customer_name'], sales_profile.name)
        self.assertEqual(kwargs['context']['refund_request_reason'], refund_request.reason)

    @mock.patch('refunds.utils.send_refund_notification.send_templated_email')
    def test_no_user_email_no_notification_sent(self, mock_send_templated_email):
        service_profile = ServiceProfileFactory(user=None, email="profile_only@example.com") # Profile has email, but no associated user
        booking = ServiceBookingFactory(service_profile=service_profile, amount_paid=Decimal("100.00"))
        payment = PaymentFactory(service_booking=booking, amount=Decimal("100.00"))
        refund_request = RefundRequestFactory(payment=payment, service_booking=booking, reason="Test reason")

        send_refund_notifications(payment, booking, "service_booking", refund_request, self.extracted_data)

        # Assert that send_templated_email was called twice (once for user, once for admin)
        # The user email should go to the profile's email
        self.assertEqual(mock_send_templated_email.call_count, 2)
        mock_send_templated_email.assert_any_call(
            recipient_list=["profile_only@example.com"],
            subject=mock.ANY,
            template_name="user_refund_processed_confirmation.html",
            context=mock.ANY,
            booking=booking,
            profile=service_profile,
        )
        # Verify the call for the admin email
        mock_send_templated_email.assert_any_call(
            recipient_list=[settings.ADMIN_EMAIL],
            subject=mock.ANY,
            template_name="admin_refund_processed_notification.html",
            context=mock.ANY,
            booking=booking,
            profile=None,
        )

    @mock.patch('refunds.utils.send_refund_notification.send_templated_email')
    def test_admin_initiated_refund_user_message(self, mock_send_templated_email):
        service_profile = ServiceProfileFactory(user=self.user)
        booking = ServiceBookingFactory(service_profile=service_profile, amount_paid=Decimal("100.00"))
        payment = PaymentFactory(service_booking=booking, amount=Decimal("100.00"))
        refund_request = RefundRequestFactory(payment=payment, service_booking=booking, reason="Admin initiated reason", is_admin_initiated=True)

        send_refund_notifications(payment, booking, "service_booking", refund_request, self.extracted_data)

        # Verify context for user email
        args, kwargs = mock_send_templated_email.call_args_list[0]
        self.assertEqual(kwargs['context']['admin_message_from_refund'], "Admin initiated reason")

    @mock.patch('refunds.utils.send_refund_notification.send_templated_email')
    def test_non_admin_initiated_refund_user_message(self, mock_send_templated_email):
        service_profile = ServiceProfileFactory(user=self.user)
        booking = ServiceBookingFactory(service_profile=service_profile, amount_paid=Decimal("100.00"))
        payment = PaymentFactory(service_booking=booking, amount=Decimal("100.00"))
        refund_request = RefundRequestFactory(payment=payment, service_booking=booking, reason="User initiated reason", is_admin_initiated=False)

        send_refund_notifications(payment, booking, "service_booking", refund_request, self.extracted_data)

        # Verify context for user email
        args, kwargs = mock_send_templated_email.call_args_list[0]
        self.assertIsNone(kwargs['context']['admin_message_from_refund'])

    @mock.patch('refunds.utils.send_refund_notification.send_templated_email')
    def test_refund_request_is_none(self, mock_send_templated_email):
        # Test with refund_request=None
        booking = ServiceBookingFactory(amount_paid=Decimal("100.00"))
        payment = PaymentFactory(service_booking=booking, amount=Decimal("100.00"))

        send_refund_notifications(payment, booking, "service_booking", None, self.extracted_data)

        # Assert only admin email was sent (as user email logic depends on refund_request)
        self.assertEqual(mock_send_templated_email.call_count, 1)
        mock_send_templated_email.assert_called_once_with(
            recipient_list=[settings.ADMIN_EMAIL],
            subject=mock.ANY,
            template_name="admin_refund_processed_notification.html",
            context=mock.ANY,
            booking=booking,
            profile=None,
        )
        # Verify context for admin email when refund_request is None
        args, kwargs = mock_send_templated_email.call_args_list[0]
        self.assertEqual(kwargs['context']['refund_request'], None)
        self.assertEqual(kwargs['context']['refund_request_reason'], "")
        self.assertEqual(kwargs['context']['refund_request_staff_notes'], "")
        self.assertEqual(kwargs['context']['booking_reference'], booking.service_booking_reference)
        self.assertIn("ID: N/A", kwargs['subject'])