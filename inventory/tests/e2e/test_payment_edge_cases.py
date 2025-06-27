import datetime
from decimal import Decimal
import stripe
from unittest import skipIf, mock

from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.conf import settings
from django.contrib.messages import get_messages

from inventory.models import TempSalesBooking, SalesBooking, Motorcycle
from payments.models import Payment
from ..test_helpers.model_factories import (
    InventorySettingsFactory,
    MotorcycleFactory,
    UserFactory,
)

@skipIf(not settings.STRIPE_SECRET_KEY, "Stripe API key not configured in settings")
@override_settings(ADMIN_EMAIL='ethan.betts.dev@gmail.com')
class TestPaymentEdgeCases(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = UserFactory()
        self.client.force_login(self.user)
        self.settings = InventorySettingsFactory(
            enable_reservation_by_deposit=True,
            deposit_amount=Decimal('200.00'),
            currency_code='AUD'
        )
        self.motorcycle = MotorcycleFactory(
            is_available=True,
            price=Decimal('15000.00'),
            status='available',
        )
        stripe.api_key = settings.STRIPE_SECRET_KEY

    @mock.patch('stripe.PaymentIntent.confirm')
    def test_failed_payment_does_not_reserve_motorcycle(self, mock_stripe_confirm):
        mock_stripe_confirm.side_effect = stripe.error.CardError(
            'Your card was declined.',
            param='card_error',
            code='card_declined'
        )
        
        initiate_url = reverse('inventory:initiate_booking', kwargs={'pk': self.motorcycle.pk})
        self.client.post(initiate_url, {'deposit_required_for_flow': 'true'})

        step1_url = reverse('inventory:step1_sales_profile')
        profile_data = {'name': 'Declined User', 'email': 'declined@example.com', 'phone_number': '555-FAIL'}
        self.client.post(step1_url, profile_data)

        step2_url = reverse('inventory:step2_booking_details_and_appointment')
        appointment_data = {'request_viewing': 'no', 'terms_accepted': 'on'}
        self.client.post(step2_url, appointment_data)

        step3_url = reverse('inventory:step3_payment')
        self.client.get(step3_url)

        self.assertEqual(Payment.objects.count(), 1)
        payment_obj = Payment.objects.first()
        payment_intent_id = payment_obj.stripe_payment_intent_id
        self.assertIsNotNone(payment_intent_id)

        with self.assertRaises(stripe.error.CardError):
            stripe.PaymentIntent.confirm(payment_intent_id)

        mock_stripe_confirm.assert_called_once_with(payment_intent_id)

        self.assertEqual(SalesBooking.objects.count(), 0, "No SalesBooking should be created for a failed payment.")

        self.motorcycle.refresh_from_db()
        self.assertTrue(self.motorcycle.is_available, "Motorcycle should still be available after a failed payment.")
        self.assertEqual(self.motorcycle.status, 'available')

        self.assertIn('temp_sales_booking_uuid', self.client.session)
        temp_booking_uuid = self.client.session['temp_sales_booking_uuid']
        self.assertTrue(TempSalesBooking.objects.filter(session_uuid=temp_booking_uuid).exists())

        payment_obj.refresh_from_db()
        self.assertNotEqual(payment_obj.status, 'succeeded', "Payment status should not be 'succeeded'.")
        self.assertNotEqual(payment_obj.status, 'failed', "Payment status should not be 'failed' unless explicitly handled.")
