import datetime
from decimal import Decimal
import stripe
from unittest import skipIf
from unittest.mock import patch

from django.test import TestCase, Client
from django.urls import reverse
from django.conf import settings
from django.core import mail

from inventory.models import TempSalesBooking, SalesBooking, SalesProfile, Motorcycle
from payments.models import Payment
from ..test_helpers.model_factories import (
    InventorySettingsFactory,
    MotorcycleFactory,
    UserFactory,
)
from payments.webhook_handlers.sales_handlers import handle_sales_booking_succeeded


@skipIf(not settings.STRIPE_SECRET_KEY, "Stripe API key not configured in settings")
class TestSalesBookingE2EWithRealAPI(TestCase):
    """
    Enhanced end-to-end tests for the multi-step sales booking process using the
    real Stripe test API to cover multiple scenarios and ensure backend robustness.
    """

    def setUp(self):
        """Set up the necessary objects for the test suite."""
        self.client = Client()
        self.user = UserFactory()
        self.client.force_login(self.user)
        self.settings = InventorySettingsFactory(
            enable_reservation_by_deposit=True,
            deposit_amount=Decimal('150.00'),
            enable_depositless_enquiry=True, # Ensure this is enabled
        )
        self.motorcycle = MotorcycleFactory(
            is_available=True,
            price=Decimal('12000.00'),
            status='available'
        )
        stripe.api_key = settings.STRIPE_SECRET_KEY

    def _perform_booking_steps_until_payment(self, deposit_required=True):
        """Helper method to run through the booking steps up to payment."""
        # --- Step 0: Initiate Booking ---
        initiate_url = reverse('inventory:initiate_booking', kwargs={'pk': self.motorcycle.pk})
        self.client.post(initiate_url, {'deposit_required_for_flow': str(deposit_required).lower()})

        # --- Step 1: Submit Profile ---
        step1_url = reverse('inventory:step1_sales_profile')
        profile_data = {'name': self.user.get_full_name(), 'email': self.user.email, 'phone_number': '123456789'}
        self.client.post(step1_url, profile_data)
        
        # --- Step 2: Submit Appointment Details ---
        step2_url = reverse('inventory:step2_booking_details_and_appointment')
        appointment_data = {
            'appointment_date': (datetime.date.today() + datetime.timedelta(days=10)).strftime('%Y-%m-%d'),
            'appointment_time': '11:00',
            'terms_accepted': 'on'
        }
        return self.client.post(step2_url, appointment_data)

    @patch('payments.webhook_handlers.sales_handlers.send_templated_email')
    def test_full_booking_flow_with_successful_deposit(self, mock_send_email):
        """
        Tests the entire user flow with a successful deposit payment,
        verifying database state, motorcycle status, and email notifications.
        """
        # --- Run initial booking steps ---
        response = self._perform_booking_steps_until_payment(deposit_required=True)
        self.assertRedirects(response, reverse('inventory:step3_payment'))

        # --- Step 3: Make Real API Call for Payment ---
        self.client.get(reverse('inventory:step3_payment'))
        payment_obj = Payment.objects.first()
        payment_intent_id = payment_obj.stripe_payment_intent_id
        
        try:
            full_return_url = f"http://testserver{reverse('inventory:step4_confirmation')}"
            stripe.PaymentIntent.confirm(
                payment_intent_id,
                payment_method="pm_card_visa",
                return_url=full_return_url,
            )
        except stripe.error.StripeError as e:
            self.fail(f"Stripe API call failed during test: {e}")

        # --- Simulate Webhook and Assert Final State ---
        updated_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        handle_sales_booking_succeeded(payment_obj, updated_intent)

        # Assertions for final state
        self.assertEqual(TempSalesBooking.objects.count(), 0)
        self.assertEqual(SalesBooking.objects.count(), 1)
        
        final_booking = SalesBooking.objects.first()
        self.assertEqual(final_booking.payment_status, 'deposit_paid')
        self.assertEqual(final_booking.amount_paid, self.settings.deposit_amount)
        self.assertEqual(final_booking.motorcycle, self.motorcycle)
        
        self.motorcycle.refresh_from_db()
        self.assertEqual(self.motorcycle.status, 'reserved')
        self.assertFalse(self.motorcycle.is_available)

        # Assert email notifications were sent (user and admin)
        self.assertEqual(mock_send_email.call_count, 2)
        
        # --- Step 4: Verify Confirmation Page ---
        confirmation_url = reverse('inventory:step4_confirmation') + f'?payment_intent_id={payment_intent_id}'
        response = self.client.get(confirmation_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, final_booking.sales_booking_reference)

    @patch('inventory.utils.convert_temp_sales_booking.send_templated_email')
    def test_depositless_enquiry_flow(self, mock_send_email):
        """
        Tests the user flow for a deposit-less enquiry, ensuring no payment
        is processed and the motorcycle is not reserved.
        """
        # --- Run booking steps for an enquiry ---
        response = self._perform_booking_steps_until_payment(deposit_required=False)
        # Should redirect straight to confirmation as no payment is needed
        self.assertRedirects(response, reverse('inventory:step4_confirmation'))
        
        # --- Assert Final State ---
        self.assertEqual(Payment.objects.count(), 0) # No payment object should be created
        self.assertEqual(TempSalesBooking.objects.count(), 0)
        self.assertEqual(SalesBooking.objects.count(), 1)

        final_booking = SalesBooking.objects.first()
        self.assertEqual(final_booking.payment_status, 'unpaid')
        self.assertEqual(final_booking.amount_paid, Decimal('0.00'))
        
        # Motorcycle should NOT be reserved
        self.motorcycle.refresh_from_db()
        self.assertEqual(self.motorcycle.status, 'available')
        self.assertTrue(self.motorcycle.is_available)

        # Assert enquiry emails were sent
        self.assertEqual(mock_send_email.call_count, 2)
    
    @patch('payments.webhook_handlers.sales_handlers.send_templated_email')
    def test_booking_flow_with_failed_payment(self, mock_send_email):
        """
        Tests the user flow where the Stripe payment fails, ensuring the booking
        is not created and the system state remains valid for a retry.
        """
        # --- Run initial booking steps ---
        response = self._perform_booking_steps_until_payment(deposit_required=True)
        self.assertRedirects(response, reverse('inventory:step3_payment'))

        # --- Step 3: Attempt Payment with a card that will be declined ---
        self.client.get(reverse('inventory:step3_payment'))
        payment_obj = Payment.objects.first()
        payment_intent_id = payment_obj.stripe_payment_intent_id
        
        with self.assertRaises(stripe.error.CardError) as e:
            full_return_url = f"http://testserver{reverse('inventory:step4_confirmation')}"
            stripe.PaymentIntent.confirm(
                payment_intent_id,
                payment_method="pm_card_visa_chargeDeclined", # This card always fails
                return_url=full_return_url,
            )
        
        # Check that the Stripe API returned the expected error
        self.assertEqual(e.exception.code, 'card_declined')

        # --- Assert Final State after Failure ---
        payment_obj.refresh_from_db()
        updated_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        
        # The payment status should reflect the failure
        self.assertEqual(payment_obj.status, 'requires_payment_method')
        self.assertEqual(updated_intent.status, 'requires_payment_method')
        
        # CRITICAL: No final booking should be created
        self.assertEqual(SalesBooking.objects.count(), 0)
        # The temporary booking should still exist for the user to retry
        self.assertEqual(TempSalesBooking.objects.count(), 1)
        
        # Motorcycle should NOT be reserved
        self.motorcycle.refresh_from_db()
        self.assertEqual(self.motorcycle.status, 'available')
        self.assertTrue(self.motorcycle.is_available)

        # No confirmation emails should have been sent
        mock_send_email.assert_not_called()
