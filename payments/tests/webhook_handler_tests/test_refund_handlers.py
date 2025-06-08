from decimal import Decimal
from django.test import TestCase, override_settings
from django.utils import timezone
from unittest import mock
from django.conf import settings
import stripe

# Import models
from hire.models import HireBooking
from payments.models import Payment, RefundRequest
from service.models import ServiceBooking # Import ServiceBooking

# Import handlers
from payments.webhook_handlers.refund_handlers import handle_booking_refunded, handle_booking_refund_updated

# Import factories
from ..test_helpers.model_factories import  (
    UserFactory,
    DriverProfileFactory,
    HireBookingFactory,
    PaymentFactory,
    RefundRequestFactory,
    ServiceBookingFactory, # Import ServiceBookingFactory
    ServiceProfileFactory, # Import ServiceProfileFactory
)

@override_settings(ADMIN_EMAIL='admin-refund@example.com', SITE_BASE_URL='http://example.com')
class RefundWebhookHandlerTest(TestCase):
    """
    Tests for the refund-related webhook handlers, now including both HireBooking and ServiceBooking.
    """
    def setUp(self):
        """Set up objects for each test, for both HireBooking and ServiceBooking."""
        self.user = UserFactory()
        self.driver_profile = DriverProfileFactory(user=self.user)
        self.service_profile = ServiceProfileFactory(user=self.user) # Setup for ServiceBooking

        # Hire Booking Setup
        self.hire_payment = PaymentFactory(
            driver_profile=self.driver_profile,
            amount=Decimal('300.00'),
            status='succeeded',
            refunded_amount=Decimal('0.00')
        )
        self.hire_booking = HireBookingFactory(
            driver_profile=self.driver_profile,
            payment=self.hire_payment,
            grand_total=self.hire_payment.amount,
            amount_paid=self.hire_payment.amount,
            payment_status='paid',
            status='confirmed'
        )
        self.hire_payment.hire_booking = self.hire_booking
        self.hire_payment.save()

        # Service Booking Setup
        self.service_payment = PaymentFactory(
            service_customer_profile=self.service_profile, # Link to service profile
            amount=Decimal('250.00'),
            status='succeeded',
            refunded_amount=Decimal('0.00')
        )
        self.service_booking = ServiceBookingFactory(
            service_profile=self.service_profile,
            payment=self.service_payment,
            calculated_total=self.service_payment.amount,
            amount_paid=self.service_payment.amount,
            payment_status='paid',
            booking_status='confirmed'
        )
        self.service_payment.service_booking = self.service_booking
        self.service_payment.save()


    # --- Hire Booking Tests (Existing, with corrected assertion for partial refund) ---

    @mock.patch('payments.webhook_handlers.refund_handlers.send_templated_email')
    def test_handle_charge_refunded_full_refund_hire_booking(self, mock_send_email):
        """
        Tests 'charge.refunded' event for a full refund for a HireBooking.
        """
        # 1. Setup
        refund_request = RefundRequestFactory(
            hire_booking=self.hire_booking,
            payment=self.hire_payment,  # Explicitly link to the correct payment
            status='approved',
            refund_calculation_details={},
            amount_to_refund=self.hire_payment.amount # Explicitly set amount_to_refund for full refund test
        )
        event_charge_object_data = {
            'object': 'charge',
            'amount_refunded': int(self.hire_payment.amount * 100),
            'refunds': {
                'data': [{'id': 're_full_123', 'status': 'succeeded', 'created': int(timezone.now().timestamp())}]
            }
        }

        # 2. Action
        handle_booking_refunded(self.hire_payment, event_charge_object_data)

        # 3. Assertions
        self.hire_payment.refresh_from_db()
        self.hire_booking.refresh_from_db()
        refund_request.refresh_from_db()

        self.assertEqual(self.hire_payment.status, 'refunded')
        self.assertEqual(self.hire_payment.refunded_amount, self.hire_payment.amount)
        self.assertEqual(self.hire_booking.status, 'cancelled')
        self.assertEqual(self.hire_booking.payment_status, 'refunded')
        self.assertEqual(refund_request.status, 'refunded')
        # Expect 2 emails: 1 to user, 1 to admin
        self.assertEqual(mock_send_email.call_count, 2)

    @mock.patch('payments.webhook_handlers.refund_handlers.send_templated_email')
    def test_handle_charge_refunded_partial_refund_hire_booking(self, mock_send_email):
        """
        Tests 'charge.refunded' event for a partial refund for a HireBooking.
        """
        partial_refund_amount = Decimal('100.00')
        refund_request = RefundRequestFactory(
            hire_booking=self.hire_booking,
            payment=self.hire_payment, # Explicitly link to the correct payment
            amount_to_refund=partial_refund_amount,
            status='approved',
            refund_calculation_details={}
        )
        event_charge_object_data = {
            'object': 'charge',
            'amount_refunded': int(partial_refund_amount * 100),
            'refunds': {
                'data': [{'id': 're_partial_123', 'status': 'succeeded', 'created': int(timezone.now().timestamp())}]
            }
        }

        handle_booking_refunded(self.hire_payment, event_charge_object_data)

        self.hire_payment.refresh_from_db()
        self.hire_booking.refresh_from_db()
        refund_request.refresh_from_db()

        self.assertEqual(self.hire_payment.status, 'partially_refunded')
        self.assertEqual(self.hire_payment.refunded_amount, partial_refund_amount)
        self.assertEqual(self.hire_booking.payment_status, 'partially_refunded')
        self.assertEqual(self.hire_booking.status, 'confirmed') # Not cancelled
        self.assertEqual(refund_request.status, 'partially_refunded')
        self.assertEqual(mock_send_email.call_count, 2)

    @mock.patch('payments.webhook_handlers.refund_handlers.send_templated_email')
    @mock.patch('stripe.Charge.retrieve')
    def test_handle_refund_updated_success_hire_booking(self, mock_stripe_charge_retrieve, mock_send_email):
        """
        Tests 'charge.refund.updated' event for a successful refund for a HireBooking.
        """
        # Create a refund request for the handler to find
        RefundRequestFactory(
            hire_booking=self.hire_booking,
            payment=self.hire_payment,
            status='approved',
            amount_to_refund=self.hire_payment.amount
        )
        mock_stripe_charge_retrieve.return_value = {
            'amount_refunded': int(self.hire_payment.amount * 100)
        }
        event_refund_object_data = {
            'object': 'refund',
            'id': 're_updated_123',
            'charge': 'ch_123',
            'status': 'succeeded',
        }

        handle_booking_refund_updated(self.hire_payment, event_refund_object_data)

        self.hire_payment.refresh_from_db()
        self.assertEqual(self.hire_payment.status, 'refunded')
        self.assertEqual(self.hire_payment.refunded_amount, self.hire_payment.amount)
        self.assertEqual(mock_send_email.call_count, 2)

    @mock.patch('payments.webhook_handlers.refund_handlers.send_templated_email')
    @mock.patch('stripe.Charge.retrieve', side_effect=stripe.error.StripeError("API Error"))
    def test_handle_refund_updated_stripe_api_fails_hire_booking(self, mock_stripe_charge_retrieve, mock_send_email):
        """
        Tests 'charge.refund.updated' falls back to event data if stripe.Charge.retrieve fails for a HireBooking.
        """
        fallback_amount = Decimal('50.00')
        # Create a refund request for the handler to find
        RefundRequestFactory(
            hire_booking=self.hire_booking,
            payment=self.hire_payment,
            status='approved',
            amount_to_refund=fallback_amount
        )
        event_refund_object_data = {
            'object': 'refund',
            'id': 're_updated_fail_123',
            'charge': 'ch_fail_123',
            'amount': int(fallback_amount * 100),
            'status': 'succeeded',
        }

        handle_booking_refund_updated(self.hire_payment, event_refund_object_data)

        self.hire_payment.refresh_from_db()
        self.assertEqual(self.hire_payment.status, 'partially_refunded')
        self.assertEqual(self.hire_payment.refunded_amount, fallback_amount)
        self.assertEqual(mock_send_email.call_count, 2)

    # --- Service Booking Tests (New) ---

    @mock.patch('payments.webhook_handlers.refund_handlers.send_templated_email')
    def test_handle_charge_refunded_full_refund_service_booking(self, mock_send_email):
        """
        Tests 'charge.refunded' event for a full refund for a ServiceBooking.
        """
        refund_request = RefundRequestFactory(
            service_booking=self.service_booking,
            payment=self.service_payment,
            status='approved',
            refund_calculation_details={},
            amount_to_refund=self.service_payment.amount
        )
        event_charge_object_data = {
            'object': 'charge',
            'amount_refunded': int(self.service_payment.amount * 100),
            'refunds': {
                'data': [{'id': 're_service_full_123', 'status': 'succeeded', 'created': int(timezone.now().timestamp())}]
            }
        }

        handle_booking_refunded(self.service_payment, event_charge_object_data)

        self.service_payment.refresh_from_db()
        self.service_booking.refresh_from_db()
        refund_request.refresh_from_db()

        self.assertEqual(self.service_payment.status, 'refunded')
        self.assertEqual(self.service_payment.refunded_amount, self.service_payment.amount)
        self.assertEqual(self.service_booking.booking_status, 'confirmed') # Service booking status should remain 'confirmed' unless declined
        self.assertEqual(self.service_booking.payment_status, 'refunded')
        self.assertEqual(refund_request.status, 'refunded')
        self.assertEqual(mock_send_email.call_count, 2) # User and Admin email

    @mock.patch('payments.webhook_handlers.refund_handlers.send_templated_email')
    def test_handle_charge_refunded_partial_refund_service_booking(self, mock_send_email):
        """
        Tests 'charge.refunded' event for a partial refund for a ServiceBooking.
        """
        partial_refund_amount = Decimal('75.00')
        refund_request = RefundRequestFactory(
            service_booking=self.service_booking,
            payment=self.service_payment,
            amount_to_refund=partial_refund_amount,
            status='approved',
            refund_calculation_details={}
        )
        event_charge_object_data = {
            'object': 'charge',
            'amount_refunded': int(partial_refund_amount * 100),
            'refunds': {
                'data': [{'id': 're_service_partial_123', 'status': 'succeeded', 'created': int(timezone.now().timestamp())}]
            }
        }

        handle_booking_refunded(self.service_payment, event_charge_object_data)

        self.service_payment.refresh_from_db()
        self.service_booking.refresh_from_db()
        refund_request.refresh_from_db()

        self.assertEqual(self.service_payment.status, 'partially_refunded')
        self.assertEqual(self.service_payment.refunded_amount, partial_refund_amount)
        self.assertEqual(self.service_booking.payment_status, 'partially_refunded')
        self.assertEqual(self.service_booking.booking_status, 'confirmed') # Not changed by partial refund
        self.assertEqual(refund_request.status, 'partially_refunded')
        self.assertEqual(mock_send_email.call_count, 2)

    @mock.patch('payments.webhook_handlers.refund_handlers.send_templated_email')
    @mock.patch('stripe.Charge.retrieve')
    def test_handle_refund_updated_success_service_booking(self, mock_stripe_charge_retrieve, mock_send_email):
        """
        Tests 'charge.refund.updated' event for a successful refund for a ServiceBooking.
        """
        RefundRequestFactory(
            service_booking=self.service_booking,
            payment=self.service_payment,
            status='approved',
            amount_to_refund=self.service_payment.amount
        )
        mock_stripe_charge_retrieve.return_value = {
            'amount_refunded': int(self.service_payment.amount * 100)
        }
        event_refund_object_data = {
            'object': 'refund',
            'id': 're_service_updated_123',
            'charge': 'ch_service_123',
            'status': 'succeeded',
        }

        handle_booking_refund_updated(self.service_payment, event_refund_object_data)

        self.service_payment.refresh_from_db()
        self.assertEqual(self.service_payment.status, 'refunded')
        self.assertEqual(self.service_payment.refunded_amount, self.service_payment.amount)
        self.assertEqual(mock_send_email.call_count, 2)

    @mock.patch('payments.webhook_handlers.refund_handlers.send_templated_email')
    @mock.patch('stripe.Charge.retrieve', side_effect=stripe.error.StripeError("API Error"))
    def test_handle_refund_updated_stripe_api_fails_service_booking(self, mock_stripe_charge_retrieve, mock_send_email):
        """
        Tests 'charge.refund.updated' falls back to event data if stripe.Charge.retrieve fails for a ServiceBooking.
        """
        fallback_amount = Decimal('25.00')
        RefundRequestFactory(
            service_booking=self.service_booking,
            payment=self.service_payment,
            status='approved',
            amount_to_refund=fallback_amount
        )
        event_refund_object_data = {
            'object': 'refund',
            'id': 're_service_updated_fail_123',
            'charge': 'ch_service_fail_123',
            'amount': int(fallback_amount * 100),
            'status': 'succeeded',
        }

        handle_booking_refund_updated(self.service_payment, event_refund_object_data)

        self.service_payment.refresh_from_db()
        self.assertEqual(self.service_payment.status, 'partially_refunded')
        self.assertEqual(self.service_payment.refunded_amount, fallback_amount)
        self.assertEqual(mock_send_email.call_count, 2)

    @mock.patch('payments.webhook_handlers.refund_handlers.send_templated_email')
    def test_handle_booking_declined_and_refunded_service_booking(self, mock_send_email):
        """
        Tests that a ServiceBooking transitions to 'DECLINED_REFUNDED' if it was declined and then fully refunded.
        """
        # Set initial status of service booking to 'declined'
        self.service_booking.booking_status = 'declined'
        self.service_booking.save()

        # Create a refund request
        refund_request = RefundRequestFactory(
            service_booking=self.service_booking,
            payment=self.service_payment,
            status='approved',
            amount_to_refund=self.service_payment.amount
        )
        event_charge_object_data = {
            'object': 'charge',
            'amount_refunded': int(self.service_payment.amount * 100),
            'refunds': {
                'data': [{'id': 're_declined_refund_123', 'status': 'succeeded', 'created': int(timezone.now().timestamp())}]
            }
        }

        handle_booking_refunded(self.service_payment, event_charge_object_data)

        self.service_payment.refresh_from_db()
        self.service_booking.refresh_from_db()
        refund_request.refresh_from_db()

        self.assertEqual(self.service_payment.status, 'refunded')
        self.assertEqual(self.service_booking.payment_status, 'refunded')
        self.assertEqual(self.service_booking.booking_status, 'DECLINED_REFUNDED') # Crucial assertion
        self.assertEqual(refund_request.status, 'refunded')
        self.assertEqual(mock_send_email.call_count, 2)

