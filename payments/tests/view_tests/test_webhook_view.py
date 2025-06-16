from django.test import TestCase, Client
from django.urls import reverse
from django.conf import settings
from django.utils import timezone
from decimal import Decimal
import json
import stripe
from unittest.mock import patch, MagicMock

from payments.models import Payment, WebhookEvent
from hire.models import TempHireBooking, HireBooking
from payments.webhook_handlers import WEBHOOK_HANDLERS

from payments.tests.test_helpers.model_factories import (
    PaymentFactory,
    TempHireBookingFactory,
    HireBookingFactory,
    DriverProfileFactory,
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
        TempHireBooking.objects.all().delete()
        HireBooking.objects.all().delete()
        
        self.driver_profile = DriverProfileFactory.create()
        self.motorcycle = MotorcycleFactory.create()

        self._original_webhook_handlers = WEBHOOK_HANDLERS.copy()
        WEBHOOK_HANDLERS.clear()
        WEBHOOK_HANDLERS['hire_booking'] = {}


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
    def test_payment_intent_succeeded_new_event(self, mock_construct_event):
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
            status='requires_confirmation'
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
        
        with patch.dict(WEBHOOK_HANDLERS['hire_booking'], {'payment_intent.succeeded': self.mock_hire_booking_succeeded_handler}):
            response = self.client.post(
                self.webhook_url,
                json.dumps(mock_event.to_dict()),
                content_type='application/json',
                HTTP_STRIPE_SIGNATURE='valid_sig'
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(WebhookEvent.objects.count(), 1)
            self.assertEqual(WebhookEvent.objects.first().stripe_event_id, mock_event.id)
            payment.refresh_from_db()
            self.assertEqual(payment.status, 'succeeded')
            self.assertEqual(payment.amount, Decimal('150.00'))
            self.assertEqual(payment.currency, 'AUD')
            
            self.assertTrue(HireBooking.objects.filter(payment=payment).exists())

    @patch('stripe.Webhook.construct_event')
    def test_payment_intent_succeeded_event_already_processed(self, mock_construct_event):
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
            self.assertEqual(WebhookEvent.objects.count(), initial_webhook_event_count)
            mock_handler_func.assert_not_called()

    @patch('stripe.Webhook.construct_event')
    def test_payment_intent_succeeded_payment_not_found(self, mock_construct_event):
        mock_event = self._generate_mock_stripe_event(
            'payment_intent.succeeded',
            'pi_not_found',
            'succeeded',
            amount=Decimal('200.00'),
            currency='AUD',
            metadata={'booking_type': 'hire_booking'}
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

            self.assertEqual(response.status_code, 200)
            self.assertEqual(WebhookEvent.objects.count(), 1)
            mock_handler_func.assert_not_called()

    @patch('stripe.Webhook.construct_event')
    def test_payment_intent_payment_failed(self, mock_construct_event):
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
            'requires_payment_method',
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
        self.assertEqual(payment.status, 'requires_payment_method')

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
            temp_hire_booking=None,
            hire_booking=None,
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
            temp_hire_booking=None,
            hire_booking=None,
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


    @patch('stripe.Webhook.construct_event')
    def test_database_error_during_webhook_event_creation(self, mock_construct_event):
        mock_event = self._generate_mock_stripe_event(
            'payment_intent.succeeded',
            'pi_db_error',
            'succeeded',
            amount=Decimal('100.00'),
            currency='AUD',
            metadata={'booking_type': 'hire_booking'}
        )
        mock_construct_event.return_value = mock_event

        with patch('payments.views.webhook_view.WebhookEvent.objects.create', side_effect=Exception("Simulated DB error")):
            response = self.client.post(
                self.webhook_url,
                json.dumps(mock_event.to_dict()),
                content_type='application/json',
                HTTP_STRIPE_SIGNATURE='valid_sig'
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(Payment.objects.count(), 0)

    def mock_hire_booking_succeeded_handler(self, payment_obj, stripe_payment_intent_data):
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
                raise Exception("TempBooking not found")

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
            pass
        except Exception as e:
            pass
