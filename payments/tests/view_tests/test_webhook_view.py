from django.test import TestCase, Client
from django.urls import reverse
from django.conf import settings
from django.utils import timezone
from decimal import Decimal
import json
import stripe
from unittest.mock import patch, MagicMock

from payments.models import Payment, WebhookEvent
from payments.webhook_handlers import WEBHOOK_HANDLERS

from payments.tests.test_helpers.model_factories import (
    PaymentFactory,
    MotorcycleFactory,
    WebhookEventFactory,
)


class StripeWebhookViewTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.webhook_url = reverse('payments:stripe_webhook')

        self._original_stripe_webhook_secret = getattr(settings, 'STRIPE_WEBHOOK_SECRET', None)
        settings.STRIPE_WEBHOOK_SECRET = 'whsec_test_secret'

        Payment.objects.all().delete()
        WebhookEvent.objects.all().delete()
        
        self.driver_profile = DriverProfileFactory.create()
        self.motorcycle = MotorcycleFactory.create()

        self._original_webhook_handlers = WEBHOOK_HANDLERS.copy()
        WEBHOOK_HANDLERS.clear()


    def _generate_mock_stripe_event(self, event_type, payment_intent_id, status, amount=None, currency='aud', metadata=None):
        if metadata is None:
            metadata = {}
        if amount is None:
            amount = Decimal('100.00')

        event_id = f'evt_{payment_intent_id}_{event_type}_{timezone.now().timestamp()}'
        event_data = {
            'id': payment_intent_id,
            'object': 'payment_intent',
            'amount': int(amount * 100),
            'currency': currency.lower(),
            'status': status,
            'metadata': metadata,
            'description': f"Mock payment for {payment_intent_id}"
        }
        mock_event = MagicMock(
            id=event_id,
            type=event_type,
            data={'object': event_data},
            api_version='2020-08-27',
            request={'id': 'req_test', 'idempotency_key': None},
            to_dict=lambda: {
                'id': event_id,
                'type': event_type,
                'data': {'object': event_data},
                'api_version': '2020-08-27',
                'request': {'id': 'req_test', 'idempotency_key': None},
            }
        )
        mock_event.__getitem__.side_effect = lambda key: {
            'id': event_id,
            'type': event_type,
            'data': {'object': event_data},
            'api_version': '2020-08-27',
            'request': {'id': 'req_test', 'idempotency_key': None},
        }.get(key, MagicMock())

        return mock_event

    def tearDown(self):
        if self._original_stripe_webhook_secret is not None:
            settings.STRIPE_WEBHOOK_SECRET = self._original_stripe_webhook_secret
        else:
            if hasattr(settings, 'STRIPE_WEBHOOK_SECRET'):
                del settings.STRIPE_WEBHOOK_SECRET
        
        WEBHOOK_HANDLERS.clear()
        WEBHOOK_HANDLERS.update(self._original_webhook_handlers)


    @patch('stripe.Webhook.construct_event')
    def test_webhook_signature_invalid(self, mock_construct_event):
        mock_construct_event.side_effect = stripe.error.SignatureVerificationError("Invalid signature", "sig_header")
        response = self.client.post(self.webhook_url, b'{}', content_type='application/json', HTTP_STRIPE_SIGNATURE='invalid_sig')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(WebhookEvent.objects.count(), 0)

    @patch('stripe.Webhook.construct_event')
    def test_webhook_payload_invalid(self, mock_construct_event):
        mock_construct_event.side_effect = ValueError("Invalid payload")
        response = self.client.post(self.webhook_url, b'not json', content_type='application/json', HTTP_STRIPE_SIGNATURE='valid_sig')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(WebhookEvent.objects.count(), 0)

    @patch('stripe.Webhook.construct_event')
    def test_unhandled_event_type(self, mock_construct_event):
        mock_event = self._generate_mock_stripe_event(
            'charge.succeeded',
            'ch_succeeded',
            'succeeded',
            amount=Decimal('50.00'),
            currency='AUD'
        )
        mock_event.type = 'charge.succeeded'
        mock_event.data = {'object': {'id': 'ch_succeeded', 'amount': 5000, 'currency': 'aud'}}
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
        self.assertEqual(Payment.objects.count(), 0)

    @patch('stripe.Webhook.construct_event')
    def test_payment_intent_no_booking_type_metadata(self, mock_construct_event):
        payment = PaymentFactory.create(
            stripe_payment_intent_id='pi_no_metadata',
            amount=Decimal('120.00'),
            currency='AUD',
            status='requires_confirmation',
            service_booking=None,
            temp_service_booking=None
        )

        mock_event = self._generate_mock_stripe_event(
            'payment_intent.succeeded',
            'pi_no_metadata',
            'succeeded',
            amount=Decimal('120.00'),
            currency='AUD',
            metadata={}
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
        payment.refresh_from_db()
        self.assertEqual(payment.status, 'succeeded')


    @patch('stripe.Webhook.construct_event')
    def test_payment_intent_unregistered_booking_type(self, mock_construct_event):
        payment = PaymentFactory.create(
            stripe_payment_intent_id='pi_unregistered_type',
            amount=Decimal('120.00'),
            currency='AUD',
            status='requires_confirmation',
            service_booking=None,
            temp_service_booking=None
        )

        mock_event = self._generate_mock_stripe_event(
            'payment_intent.succeeded',
            'pi_unregistered_type',
            'succeeded',
            amount=Decimal('120.00'),
            currency='AUD',
            metadata={'booking_type': 'unregistered_type'}
        )
        mock_construct_event.return_value = mock_event

        response = self.client.post(
            self.webhook_url,
            json.dumps(mock_event.to_dict()),
            content_type='application/json',
            HTTP_STRIPE_SIGNATURE='valid_sig'
        )
        self.assertEqual(response.status_code, 200)


    