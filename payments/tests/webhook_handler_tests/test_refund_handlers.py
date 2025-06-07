from decimal import Decimal
from django.test import TestCase, override_settings
from django.utils import timezone
from unittest import mock
from django.conf import settings
import stripe

# Import models
from hire.models import HireBooking
from payments.models import Payment, HireRefundRequest

# Import handlers
from payments.webhook_handlers.refund_handlers import handle_hire_booking_refunded, handle_hire_booking_refund_updated

# Import factories
from ..test_helpers.model_factories import  (
    UserFactory,
    DriverProfileFactory,
    HireBookingFactory,
    PaymentFactory,
    HireRefundRequestFactory,
)

@override_settings(ADMIN_EMAIL='admin-refund@example.com', SITE_BASE_URL='http://example.com')
class RefundWebhookHandlerTest(TestCase):
    """
    Tests for the refund-related webhook handlers.
    """
    def setUp(self):
        """Set up objects for each test."""
        self.user = UserFactory()
        self.driver_profile = DriverProfileFactory(user=self.user)
        self.payment = PaymentFactory(
            driver_profile=self.driver_profile,
            amount=Decimal('300.00'),
            status='succeeded',
            refunded_amount=Decimal('0.00')
        )
        self.hire_booking = HireBookingFactory(
            driver_profile=self.driver_profile,
            payment=self.payment,
            grand_total=self.payment.amount,
            amount_paid=self.payment.amount,
            payment_status='paid',
            status='confirmed'
        )
        self.payment.hire_booking = self.hire_booking
        self.payment.save()

    @mock.patch('payments.webhook_handlers.refund_handlers.send_templated_email')
    def test_handle_charge_refunded_full_refund(self, mock_send_email):
        """
        Tests 'charge.refunded' event for a full refund.
        """
        # 1. Setup
        refund_request = HireRefundRequestFactory(
            hire_booking=self.hire_booking,
            status='approved'
        )
        event_charge_object_data = {
            'object': 'charge',
            'amount_refunded': int(self.payment.amount * 100),
            'refunds': {
                'data': [{'id': 're_full_123', 'status': 'succeeded', 'created': int(timezone.now().timestamp())}]
            }
        }

        # 2. Action
        handle_hire_booking_refunded(self.payment, event_charge_object_data)

        # 3. Assertions
        self.payment.refresh_from_db()
        self.hire_booking.refresh_from_db()
        refund_request.refresh_from_db()

        self.assertEqual(self.payment.status, 'refunded')
        self.assertEqual(self.payment.refunded_amount, self.payment.amount)
        self.assertEqual(self.hire_booking.status, 'cancelled')
        self.assertEqual(self.hire_booking.payment_status, 'refunded')
        self.assertEqual(refund_request.status, 'refunded')
        self.assertEqual(mock_send_email.call_count, 2)

    @mock.patch('payments.webhook_handlers.refund_handlers.send_templated_email')
    def test_handle_charge_refunded_partial_refund(self, mock_send_email):
        """
        Tests 'charge.refunded' event for a partial refund.
        """
        partial_refund_amount = Decimal('100.00')
        refund_request = HireRefundRequestFactory(
            hire_booking=self.hire_booking,
            amount_to_refund=partial_refund_amount,
            status='approved'
        )
        event_charge_object_data = {
            'object': 'charge',
            'amount_refunded': int(partial_refund_amount * 100),
            'refunds': {
                'data': [{'id': 're_partial_123', 'status': 'succeeded', 'created': int(timezone.now().timestamp())}]
            }
        }

        handle_hire_booking_refunded(self.payment, event_charge_object_data)

        self.payment.refresh_from_db()
        self.hire_booking.refresh_from_db()
        self.assertEqual(self.payment.status, 'partially_refunded')
        self.assertEqual(self.payment.refunded_amount, partial_refund_amount)
        self.assertEqual(self.hire_booking.payment_status, 'partially_refunded')
        self.assertEqual(self.hire_booking.status, 'confirmed') # Not cancelled
        self.assertEqual(mock_send_email.call_count, 2)

    @mock.patch('payments.webhook_handlers.refund_handlers.send_templated_email')
    @mock.patch('stripe.Charge.retrieve')
    def test_handle_refund_updated_success(self, mock_stripe_charge_retrieve, mock_send_email):
        """
        Tests 'charge.refund.updated' event for a successful refund.
        """
        mock_stripe_charge_retrieve.return_value = {
            'amount_refunded': int(self.payment.amount * 100)
        }
        event_refund_object_data = {
            'object': 'refund',
            'id': 're_updated_123',
            'charge': 'ch_123',
            'status': 'succeeded',
        }

        handle_hire_booking_refund_updated(self.payment, event_refund_object_data)

        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, 'refunded')
        self.assertEqual(self.payment.refunded_amount, self.payment.amount)
        self.assertEqual(mock_send_email.call_count, 2)

    @mock.patch('payments.webhook_handlers.refund_handlers.send_templated_email')
    @mock.patch('stripe.Charge.retrieve', side_effect=stripe.error.StripeError("API Error"))
    def test_handle_refund_updated_stripe_api_fails(self, mock_stripe_charge_retrieve, mock_send_email):
        """
        Tests 'charge.refund.updated' falls back to event data if stripe.Charge.retrieve fails.
        """
        fallback_amount = Decimal('50.00')
        event_refund_object_data = {
            'object': 'refund',
            'id': 're_updated_fail_123',
            'charge': 'ch_fail_123',
            'amount': int(fallback_amount * 100),
            'status': 'succeeded',
        }

        handle_hire_booking_refund_updated(self.payment, event_refund_object_data)

        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, 'partially_refunded')
        self.assertEqual(self.payment.refunded_amount, fallback_amount)
        self.assertEqual(mock_send_email.call_count, 2)

