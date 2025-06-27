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
# Note: We are deliberately NOT importing the webhook handler,
# as a failed payment should never trigger it.

@skipIf(not settings.STRIPE_SECRET_KEY, "Stripe API key not configured in settings")
@override_settings(ADMIN_EMAIL='ethan.betts.dev@gmail.com')
class TestPaymentEdgeCases(TestCase):
    """
    Tests for handling payment failures, race conditions, and other
    edge cases in the E2E booking process.
    """

    def setUp(self):
        """Set up the basic environment for edge case tests."""
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

    def test_failed_payment_does_not_reserve_motorcycle(self):
        """
        Ensures that when a Stripe payment is declined, the application state
        remains unchanged and the motorcycle is not reserved.
        """
        # --- Step 1 & 2: User completes their details ---
        initiate_url = reverse('inventory:initiate_booking', kwargs={'pk': self.motorcycle.pk})
        self.client.post(initiate_url, {'deposit_required_for_flow': 'true'})

        step1_url = reverse('inventory:step1_sales_profile')
        profile_data = {'name': 'Declined User', 'email': 'declined@example.com', 'phone_number': '555-FAIL'}
        self.client.post(step1_url, profile_data)

        step2_url = reverse('inventory:step2_booking_details_and_appointment')
        appointment_data = {'request_viewing': 'no', 'terms_accepted': 'on'}
        self.client.post(step2_url, appointment_data)

        # --- Step 3: User reaches payment page ---
        step3_url = reverse('inventory:step3_payment')
        self.client.get(step3_url)

        # A Payment object and a Payment Intent should have been created
        self.assertEqual(Payment.objects.count(), 1)
        payment_obj = Payment.objects.first()
        payment_intent_id = payment_obj.stripe_payment_intent_id
        self.assertIsNotNone(payment_intent_id)

        # --- Simulate a FAILED payment attempt ---
        # We use a special Stripe test payment method that always fails.
        # We wrap this in a try/except block because Stripe's library will
        # raise an exception for a declined card, which is the expected behavior.
        try:
            stripe.PaymentIntent.confirm(
                payment_intent_id,
                payment_method="pm_card_charge_declined" # This card is designed by Stripe to fail
            )
            # If this line is reached, the test fails because Stripe should have raised an error
            self.fail("Stripe should have raised a CardError for the declined payment.")
        except stripe.error.CardError as e:
            # This is the expected outcome. We can inspect the error if needed.
            self.assertIn("Your card was declined", str(e))
            pass # Continue the test

        # --- Assertions: Verify the application state ---

        # 1. No SalesBooking should be created.
        self.assertEqual(SalesBooking.objects.count(), 0, "No SalesBooking should be created for a failed payment.")

        # 2. The Motorcycle should remain available.
        self.motorcycle.refresh_from_db()
        self.assertTrue(self.motorcycle.is_available, "Motorcycle should still be available after a failed payment.")
        self.assertEqual(self.motorcycle.status, 'available')

        # 3. The original TempSalesBooking should still exist in the session.
        self.assertIn('temp_sales_booking_uuid', self.client.session)
        temp_booking_uuid = self.client.session['temp_sales_booking_uuid']
        self.assertTrue(TempSalesBooking.objects.filter(session_uuid=temp_booking_uuid).exists())

        # 4. The Payment object's status should reflect the failure.
        payment_obj.refresh_from_db()
        self.assertEqual(payment_obj.status, 'failed', "Payment object status should be 'failed'.")
