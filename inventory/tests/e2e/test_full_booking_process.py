import datetime
import time
from decimal import Decimal
import stripe
from unittest import skipIf

from django.test import TestCase, Client
from django.urls import reverse
from django.conf import settings

from inventory.models import TempSalesBooking, SalesBooking, SalesProfile, Motorcycle
from payments.models import Payment
from ..test_helpers.model_factories import (
    InventorySettingsFactory,
    MotorcycleFactory,
    UserFactory,
    SalesProfileFactory,
)
from payments.webhook_handlers.sales_handlers import handle_sales_booking_succeeded

# This decorator will skip the test if a Stripe secret key is not configured
@skipIf(not settings.STRIPE_SECRET_KEY, "Stripe API key not configured in settings")
class TestSalesBookingE2EWithRealAPI(TestCase):
    """
    End-to-end tests for the multi-step sales booking process using the
    real Stripe test API to ensure integration is working.
    """

    def setUp(self):
        """Set up the necessary objects for the test suite."""
        self.client = Client()
        self.user = UserFactory()
        self.client.force_login(self.user)
        self.settings = InventorySettingsFactory(
            enable_reservation_by_deposit=True,
            deposit_amount=Decimal('150.00')
        )
        self.motorcycle = MotorcycleFactory(
            is_available=True,
            price=Decimal('12000.00'),
            status='available'
        )
        # Set the Stripe API key for this test
        stripe.api_key = settings.STRIPE_SECRET_KEY

    def test_full_booking_flow_with_real_stripe_payment(self):
        """
        Tests the entire user flow making a real payment confirmation call
        to the Stripe test API.
        """
        # --- Step 0 & 1: Initiate Booking and Submit Profile ---
        initiate_url = reverse('inventory:initiate_booking', kwargs={'pk': self.motorcycle.pk})
        self.client.post(initiate_url, {'deposit_required_for_flow': 'true'})
        
        step1_url = reverse('inventory:step1_sales_profile')
        profile_data = {'name': 'Test User', 'email': 'test@example.com', 'phone_number': '123'}
        self.client.post(step1_url, profile_data)
        
        # --- Step 2: Submit Appointment Details ---
        step2_url = reverse('inventory:step2_booking_details_and_appointment')
        appointment_data = {'appointment_date': '2025-08-01', 'appointment_time': '11:00', 'terms_accepted': 'on'}
        response = self.client.post(step2_url, appointment_data)
        self.assertRedirects(response, reverse('inventory:step3_payment'))

        # --- Step 3: Load Payment Page & Make Real API Call ---
        step3_url = reverse('inventory:step3_payment')
        response = self.client.get(step3_url)
        self.assertEqual(response.status_code, 200)

        # A Payment object and PaymentIntent should have been created.
        self.assertEqual(Payment.objects.count(), 1)
        payment_obj = Payment.objects.first()
        payment_intent_id = payment_obj.stripe_payment_intent_id
        self.assertIsNotNone(payment_intent_id)

        # ** MAKE REAL STRIPE API CALL **
        # Confirm the PaymentIntent using a test payment method provided by Stripe.
        # This simulates the user entering their card details and clicking "Pay".
        try:
            # For modern payment flows, Stripe requires a return_url even for tests.
            # This is where the user would be redirected after authenticating.
            confirmation_url_path = reverse('inventory:step4_confirmation')
            # The test server host is 'testserver' by convention in Django tests.
            full_return_url = f"http://testserver{confirmation_url_path}"

            stripe.PaymentIntent.confirm(
                payment_intent_id,
                payment_method="pm_card_visa", # This is Stripe's test card that always succeeds.
                return_url=full_return_url, # The required return_url is now provided.
            )
        except stripe.error.StripeError as e:
            self.fail(f"Stripe API call failed during test: {e}")

        # The above call is asynchronous on Stripe's side. The webhook might take a
        # moment to arrive. We will simulate that by directly calling the handler,
        # which is what would happen in the real world when the webhook is received.
        
        # ** SIMULATE THE WEBHOOK ARRIVING **
        # Retrieve the updated payment intent data from Stripe after confirmation.
        updated_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        
        # Manually call our webhook handler with this real data.
        handle_sales_booking_succeeded(payment_obj, updated_intent)

        # --- Assert Final State ---
        # Check that the webhook handler did its job correctly.
        self.assertEqual(TempSalesBooking.objects.count(), 0)
        self.assertEqual(SalesBooking.objects.count(), 1)
        
        final_booking = SalesBooking.objects.first()
        self.assertEqual(final_booking.payment_status, 'deposit_paid')
        self.motorcycle.refresh_from_db()
        self.assertEqual(self.motorcycle.status, 'reserved')

        # --- Step 4: User is Redirected to Confirmation ---
        # The user's browser is now redirected to the confirmation page.
        confirmation_url = reverse('inventory:step4_confirmation') + f'?payment_intent_id={payment_intent_id}'
        response = self.client.get(confirmation_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, final_booking.sales_booking_reference)
        self.assertNotContains(response, "Your booking is currently being finalized")
