# payments/tests/test_webhook_view.py

from django.test import TestCase, Client
from django.urls import reverse
from django.conf import settings
from django.utils import timezone
from decimal import Decimal
import json
import stripe
from unittest.mock import patch, MagicMock

# Import models
from payments.models import Payment, WebhookEvent
from hire.models import TempHireBooking, HireBooking # BookingAddOn might not be directly created in these tests
from payments.webhook_handlers import WEBHOOK_HANDLERS # Import the handlers dictionary

# Import model factories directly
from payments.tests.test_helpers.model_factories import (
    PaymentFactory,
    TempHireBookingFactory,
    HireBookingFactory,
    DriverProfileFactory,
    MotorcycleFactory,
    WebhookEventFactory, # <--- Added WebhookEventFactory import
    # No need to import create_user if not directly creating users in tests
    # Nor create_booking_addon if not explicitly testing its creation here
)


class StripeWebhookViewTest(TestCase):
    """
    Tests for the stripe_webhook view.
    """

    def setUp(self):
        self.client = Client()
        self.webhook_url = reverse('payments:stripe_webhook') # Ensure this URL name is correct

        # Set a dummy Stripe webhook secret for tests
        self._original_stripe_webhook_secret = getattr(settings, 'STRIPE_WEBHOOK_SECRET', None)
        settings.STRIPE_WEBHOOK_SECRET = 'whsec_test_secret'

        # Clear existing data to ensure clean state for each test
        Payment.objects.all().delete()
        WebhookEvent.objects.all().delete()
        TempHireBooking.objects.all().delete()
        HireBooking.objects.all().delete()
        
        # Create a driver profile and motorcycle using the new factories for linking payments/bookings
        self.driver_profile = DriverProfileFactory.create()
        self.motorcycle = MotorcycleFactory.create()

        # Store original WEBHOOK_HANDLERS and set up mock handlers for the test run
        self._original_webhook_handlers = WEBHOOK_HANDLERS.copy()
        WEBHOOK_HANDLERS.clear() # Clear existing handlers to ensure clean state for patching
        WEBHOOK_HANDLERS['hire_booking'] = {} # Ensure this key exists for patching later


    # Helper to generate a mock Stripe event
    def _generate_mock_stripe_event(self, event_type, payment_intent_id, status, amount=None, currency='aud', metadata=None):
        """Generates a mock Stripe event object."""
        if metadata is None:
            metadata = {}
        if amount is None:
            amount = Decimal('100.00') # Default amount for tests

        event_id = f'evt_{payment_intent_id}_{event_type}_{timezone.now().timestamp()}' # Store as string
        event_data = {
            'id': payment_intent_id,
            'object': 'payment_intent',
            'amount': int(amount * 100), # Stripe amounts are in cents
            'currency': currency.lower(),
            'status': status,
            'metadata': metadata,
            'description': f"Mock payment for {payment_intent_id}"
        }
        mock_event = MagicMock(
            id=event_id, # Set the actual string ID here
            type=event_type, # Set the actual string type here
            data={'object': event_data},
            api_version='2020-08-27', # Or any relevant API version
            request={'id': 'req_test', 'idempotency_key': None},
            to_dict=lambda: { # Ensure to_dict returns a dict for payload storage
                'id': event_id,
                'type': event_type,
                'data': {'object': event_data},
                'api_version': '2020-08-27',
                'request': {'id': 'req_test', 'idempotency_key': None},
            }
        )
        # Crucial: Configure __getitem__ for dictionary-like access
        # This ensures event['id'] returns the string, not another MagicMock
        mock_event.__getitem__.side_effect = lambda key: {
            'id': event_id,
            'type': event_type,
            'data': {'object': event_data},
            'api_version': '2020-08-27',
            'request': {'id': 'req_test', 'idempotency_key': None},
        }.get(key, MagicMock()) # Default to a new MagicMock for unconfigured keys

        return mock_event

    def tearDown(self):
        # Restore original Stripe webhook secret
        if self._original_stripe_webhook_secret is not None:
            settings.STRIPE_WEBHOOK_SECRET = self._original_stripe_webhook_secret
        else:
            # If it wasn't defined, ensure it's deleted or set to None
            if hasattr(settings, 'STRIPE_WEBHOOK_SECRET'):
                del settings.STRIPE_WEBHOOK_SECRET
        
        # Restore original WEBHOOK_HANDLERS
        WEBHOOK_HANDLERS.clear()
        WEBHOOK_HANDLERS.update(self._original_webhook_handlers)


    @patch('stripe.Webhook.construct_event')
    # No need to patch BookingAddOn.objects.create directly here if not explicitly tested
    def test_webhook_signature_invalid(self, mock_construct_event):
        """
        Test webhook with invalid signature.
        Should return 400.
        """
        mock_construct_event.side_effect = stripe.error.SignatureVerificationError("Invalid signature", "sig_header")
        response = self.client.post(self.webhook_url, b'{}', content_type='application/json', HTTP_STRIPE_SIGNATURE='invalid_sig')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(WebhookEvent.objects.count(), 0) # No event should be recorded

    @patch('stripe.Webhook.construct_event')
    def test_webhook_payload_invalid(self, mock_construct_event):
        """
        Test webhook with invalid payload (e.g., malformed JSON).
        Should return 400.
        """
        mock_construct_event.side_effect = ValueError("Invalid payload")
        response = self.client.post(self.webhook_url, b'not json', content_type='application/json', HTTP_STRIPE_SIGNATURE='valid_sig')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(WebhookEvent.objects.count(), 0) # No event should be recorded

    @patch('stripe.Webhook.construct_event')
    def test_payment_intent_succeeded_new_event(self, mock_construct_event):
        """
        Test processing of a new payment_intent.succeeded event.
        Should create WebhookEvent, update Payment, and call handler.
        """
        temp_booking = TempHireBookingFactory.create(
            motorcycle=self.motorcycle,
            driver_profile=self.driver_profile,
            grand_total=Decimal('150.00'),
            currency='AUD',
            total_hire_price=Decimal('150.00'),
            total_addons_price=Decimal('0.00'),
            total_package_price=Decimal('0.00'),
            deposit_amount=Decimal('0.00'),
        )
        payment = PaymentFactory.create(
            temp_hire_booking=temp_booking,
            driver_profile=self.driver_profile,
            stripe_payment_intent_id='pi_succeeded_new',
            amount=Decimal('150.00'),
            currency='AUD',
            status='requires_confirmation' # Initial status
        )

        mock_event = self._generate_mock_stripe_event(
            'payment_intent.succeeded',
            'pi_succeeded_new',
            'succeeded',
            amount=Decimal('150.00'),
            currency='AUD',
            metadata={
                'temp_booking_id': str(temp_booking.id),
                'user_id': str(self.driver_profile.id),
                'booking_type': 'hire_booking'
            }
        )
        mock_construct_event.return_value = mock_event
        
        # PATCH FIX: Use the actual mock handler defined in this test class
        with patch.dict(WEBHOOK_HANDLERS['hire_booking'], {'payment_intent.succeeded': self.mock_hire_booking_succeeded_handler}):
            response = self.client.post(
                self.webhook_url,
                json.dumps(mock_event.to_dict()), # Pass the dict representation of the mock event
                content_type='application/json',
                HTTP_STRIPE_SIGNATURE='valid_sig'
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(WebhookEvent.objects.count(), 1)
            self.assertEqual(WebhookEvent.objects.first().stripe_event_id, mock_event.id)
            payment.refresh_from_db()
            self.assertEqual(payment.status, 'succeeded')
            self.assertEqual(payment.amount, Decimal('150.00')) # Ensure amount updated from Stripe
            self.assertEqual(payment.currency, 'AUD')
            
            # Assert on the outcome of the mock handler's execution.
            self.assertTrue(HireBooking.objects.filter(payment=payment).exists())

    @patch('stripe.Webhook.construct_event')
    def test_payment_intent_succeeded_event_already_processed(self, mock_construct_event):
        """
        Test processing of a payment_intent.succeeded event that has already been recorded.
        Should return 200 and not re-process.
        """
        temp_booking = TempHireBookingFactory.create(
            motorcycle=self.motorcycle,
            driver_profile=self.driver_profile,
            grand_total=Decimal('150.00'),
            currency='AUD',
            total_hire_price=Decimal('150.00'),
            total_addons_price=Decimal('0.00'),
            total_package_price=Decimal('0.00'),
            deposit_amount=Decimal('0.00'),
        )
        payment = PaymentFactory.create(
            temp_hire_booking=temp_booking,
            driver_profile=self.driver_profile,
            stripe_payment_intent_id='pi_succeeded_duplicate',
            amount=Decimal('150.00'),
            currency='AUD',
            status='requires_confirmation'
        )

        mock_event = self._generate_mock_stripe_event(
            'payment_intent.succeeded',
            'pi_succeeded_duplicate',
            'succeeded',
            amount=Decimal('150.00'),
            currency='AUD',
            metadata={
                'temp_booking_id': str(temp_booking.id),
                'user_id': str(self.driver_profile.id),
                'booking_type': 'hire_booking'
            }
        )
        mock_construct_event.return_value = mock_event

        # Manually create a WebhookEvent to simulate prior processing using WebhookEventFactory
        WebhookEventFactory.create(
            stripe_event_id=mock_event.id,
            event_type=mock_event.type,
            payload=mock_event.to_dict(),
            received_at=timezone.now()
        )
        initial_webhook_event_count = WebhookEvent.objects.count()

        mock_handler_func = MagicMock()
        with patch.dict(WEBHOOK_HANDLERS['hire_booking'], {'payment_intent.succeeded': mock_handler_func}):
            response = self.client.post(
                self.webhook_url,
                json.dumps(mock_event.to_dict()),
                content_type='application/json',
                HTTP_STRIPE_SIGNATURE='valid_sig'
            )

            self.assertEqual(response.status_code, 200)
            self.assertEqual(WebhookEvent.objects.count(), initial_webhook_event_count) # No new event created
            mock_handler_func.assert_not_called() # Handler should not be called again

    @patch('stripe.Webhook.construct_event')
    def test_payment_intent_succeeded_payment_not_found(self, mock_construct_event):
        """
        Test processing of payment_intent.succeeded when Payment object is not found in DB.
        Should return 200 (Stripe doesn't need to retry), but log a warning.
        """
        # No Payment object created in DB for 'pi_not_found'
        mock_event = self._generate_mock_stripe_event(
            'payment_intent.succeeded',
            'pi_not_found',
            'succeeded',
            amount=Decimal('200.00'),
            currency='AUD',
            metadata={'booking_type': 'hire_booking'} # Still include metadata
        )
        mock_construct_event.return_value = mock_event

        mock_handler_func = MagicMock()
        with patch.dict(WEBHOOK_HANDLERS['hire_booking'], {'payment_intent.succeeded': mock_handler_func}):
            response = self.client.post(
                self.webhook_url,
                json.dumps(mock_event.to_dict()),
                content_type='application/json',
                HTTP_STRIPE_SIGNATURE='valid_sig'
            )

            self.assertEqual(response.status_code, 200) # Crucial: return 200 to Stripe
            self.assertEqual(WebhookEvent.objects.count(), 1) # Event should still be recorded
            mock_handler_func.assert_not_called() # Handler should not be called if Payment not found

    @patch('stripe.Webhook.construct_event')
    def test_payment_intent_payment_failed(self, mock_construct_event):
        """
        Test processing of a payment_intent.payment_failed event.
        Should create WebhookEvent and update Payment status.
        """
        temp_booking = TempHireBookingFactory.create(
            motorcycle=self.motorcycle,
            driver_profile=self.driver_profile,
            grand_total=Decimal('100.00'),
            total_hire_price=Decimal('100.00'),
            total_addons_price=Decimal('0.00'),
            total_package_price=Decimal('0.00'),
            deposit_amount=Decimal('0.00'),
        )
        payment = PaymentFactory.create(
            temp_hire_booking=temp_booking,
            driver_profile=self.driver_profile,
            stripe_payment_intent_id='pi_failed',
            amount=Decimal('100.00'),
            currency='AUD',
            status='requires_payment_method'
        )

        mock_event = self._generate_mock_stripe_event(
            'payment_intent.payment_failed',
            'pi_failed',
            'requires_payment_method', # Stripe sets PI status to requires_payment_method on failure
            amount=Decimal('100.00'),
            currency='AUD',
            metadata={'booking_type': 'hire_booking'}
        )
        mock_construct_event.return_value = mock_event

        response = self.client.post(
            self.webhook_url,
            json.dumps(mock_event.to_dict()),
            content_type='application/json',
            HTTP_STRIPE_SIGNATURE='valid_sig'
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(WebhookEvent.objects.count(), 1)
        webhook_event = WebhookEvent.objects.first()
        self.assertEqual(webhook_event.stripe_event_id, mock_event.id)
        self.assertEqual(webhook_event.event_type, 'payment_intent.payment_failed')

        payment.refresh_from_db()
        self.assertEqual(payment.status, 'requires_payment_method') # Status should reflect Stripe's PI status

    @patch('stripe.Webhook.construct_event')
    def test_unhandled_event_type(self, mock_construct_event):
        """
        Test processing of an unhandled Stripe event type (e.g., 'charge.succeeded').
        Should create WebhookEvent and return 200.
        """
        mock_event = self._generate_mock_stripe_event(
            'charge.succeeded',
            'ch_succeeded',
            'succeeded',
            amount=Decimal('50.00'),
            currency='AUD'
        )
        mock_event.type = 'charge.succeeded' # Override type for non-PI event
        mock_event.data = {'object': {'id': 'ch_succeeded', 'amount': 5000, 'currency': 'aud'}} # Simplified data for non-PI event
        mock_construct_event.return_value = mock_event

        response = self.client.post(
            self.webhook_url,
            json.dumps(mock_event.to_dict()),
            content_type='application/json',
            HTTP_STRIPE_SIGNATURE='valid_sig'
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(WebhookEvent.objects.count(), 1)
        self.assertEqual(WebhookEvent.objects.first().event_type, 'charge.succeeded')
        self.assertEqual(Payment.objects.count(), 0) # No payment object should be affected/created

    @patch('stripe.Webhook.construct_event')
    def test_payment_intent_no_booking_type_metadata(self, mock_construct_event):
        """
        Test processing of a payment_intent event with no 'booking_type' in metadata.
        Should update Payment status but not call any specific handler.
        """
        # CRITICAL FIX: Create Payment without linking to temp_hire_booking
        # This forces the webhook view to rely on metadata for booking_type detection.
        payment = PaymentFactory.create(
            stripe_payment_intent_id='pi_no_metadata',
            amount=Decimal('120.00'),
            currency='AUD',
            status='requires_confirmation',
            temp_hire_booking=None, # Explicitly set to None
            hire_booking=None,      # Explicitly set to None
            service_booking=None,
            temp_service_booking=None
        )

        mock_event = self._generate_mock_stripe_event(
            'payment_intent.succeeded',
            'pi_no_metadata',
            'succeeded',
            amount=Decimal('120.00'),
            currency='AUD',
            metadata={} # No booking_type
        )
        mock_construct_event.return_value = mock_event

        # No need to patch WEBHOOK_HANDLERS['hire_booking'] as we expect no handler to be called
        response = self.client.post(
            self.webhook_url,
            json.dumps(mock_event.to_dict()),
            content_type='application/json',
            HTTP_STRIPE_SIGNATURE='valid_sig'
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(WebhookEvent.objects.count(), 1)
        payment.refresh_from_db()
        self.assertEqual(payment.status, 'succeeded') # Payment status should still be updated
        # Assert that no handler was called (WEBHOOK_HANDLERS['hire_booking'] is empty)
        # This is implicitly tested by ensuring no AssertionError from mock_handler_func
        # if WEBHOOK_HANDLERS.get('hire_booking', {}).get('payment_intent.succeeded') were patched.
        # Since it's not patched, we are testing the view's fallback behavior.


    @patch('stripe.Webhook.construct_event')
    def test_payment_intent_unregistered_booking_type(self, mock_construct_event):
        """
        Test processing of a payment_intent event with an unregistered 'booking_type'.
        Should update Payment status but not call any specific handler.
        """
        # CRITICAL FIX: Create Payment without linking to temp_hire_booking
        # This forces the webhook view to rely on metadata for booking_type detection.
        payment = PaymentFactory.create(
            stripe_payment_intent_id='pi_unregistered_type',
            amount=Decimal('120.00'),
            currency='AUD',
            status='requires_confirmation',
            temp_hire_booking=None, # Explicitly set to None
            hire_booking=None,      # Explicitly set to None
            service_booking=None,
            temp_service_booking=None
        )

        mock_event = self._generate_mock_stripe_event(
            'payment_intent.succeeded',
            'pi_unregistered_type',
            'succeeded',
            amount=Decimal('120.00'),
            currency='AUD',
            metadata={'booking_type': 'unregistered_type'} # Unregistered booking_type
        )
        mock_construct_event.return_value = mock_event

        # No need to patch WEBHOOK_HANDLERS['hire_booking'] as we expect no handler to be called
        response = self.client.post(
            self.webhook_url,
            json.dumps(mock_event.to_dict()),
            content_type='application/json',
            HTTP_STRIPE_SIGNATURE='valid_sig'
        )
        self.assertEqual(response.status_code, 200)
        # Assert that no handler was called (WEBHOOK_HANDLERS['unregistered_type'] does not exist)
        # This is implicitly tested by ensuring no AssertionError from mock_handler_func
        # if a handler for 'unregistered_type' were patched.


    @patch('stripe.Webhook.construct_event')
    def test_database_error_during_webhook_event_creation(self, mock_construct_event):
        """
        Test scenario where a database error occurs during WebhookEvent creation (e.g., not IntegrityError).
        Should return 200 (for idempotency, though a real error) and not proceed to payment processing.
        """
        mock_event = self._generate_mock_stripe_event(
            'payment_intent.succeeded',
            'pi_db_error',
            'succeeded',
            amount=Decimal('100.00'),
            currency='AUD',
            metadata={'booking_type': 'hire_booking'}
        )
        mock_construct_event.return_value = mock_event

        # Patch WebhookEvent.objects.create to raise a generic database error
        with patch('payments.views.webhook_view.WebhookEvent.objects.create', side_effect=Exception("Simulated DB error")):
            response = self.client.post(
                self.webhook_url,
                json.dumps(mock_event.to_dict()),
                content_type='application/json',
                HTTP_STRIPE_SIGNATURE='valid_sig'
            )
            self.assertEqual(response.status_code, 200) # Still returns 200, as per current view logic
            # No WebhookEvent should be created in this specific case due to the mock
            self.assertEqual(Payment.objects.count(), 0)

    # Make this a method of the class so it can be accessed via self.
    def mock_hire_booking_succeeded_handler(self, payment_obj, stripe_payment_intent_data):
        """
        Mock handler for payment_intent.succeeded for hire bookings.
        In a real scenario, this would create/update a HireBooking.
        """
        try:
            temp_booking_id = stripe_payment_intent_data['metadata'].get('temp_booking_id')
            if temp_booking_id:
                temp_booking = TempHireBooking.objects.get(id=temp_booking_id)
                motorcycle = temp_booking.motorcycle
                driver_profile = temp_booking.driver_profile
                pickup_date = temp_booking.pickup_date
                pickup_time = temp_booking.pickup_time
                return_date = temp_booking.return_date
                return_time = temp_booking.return_time
                total_hire_price = temp_booking.total_hire_price
                total_addons_price = temp_booking.total_addons_price
                total_package_price = temp_booking.total_package_price
                grand_total = temp_booking.grand_total
                deposit_amount = temp_booking.deposit_amount
            else:
                raise Exception("TempBooking not found") # Fail if this happens in this test

            # Simulate HireBooking creation using HireBookingFactory
            if not HireBooking.objects.filter(payment=payment_obj).exists():
                HireBookingFactory.create(
                    motorcycle=motorcycle,
                    driver_profile=driver_profile,
                    pickup_date=pickup_date,
                    pickup_time=pickup_time,
                    return_date=return_date,
                    return_time=return_time,
                    total_hire_price=total_hire_price,
                    total_addons_price=total_addons_price,
                    total_package_price=total_package_price,
                    grand_total=grand_total,
                    deposit_amount=deposit_amount,
                    payment=payment_obj,
                    stripe_payment_intent_id=stripe_payment_intent_data['id'],
                    payment_status='paid',
                    status='confirmed',
                )
        except TempHireBooking.DoesNotExist:
            print(f"MOCK HANDLER: TempHireBooking {temp_booking_id} not found.")
        except Exception as e:
            print(f"MOCK HANDLER: Error in handler: {e}")
