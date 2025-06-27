import datetime
from decimal import Decimal
import stripe
from unittest import skipIf, mock

from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.conf import settings

from inventory.models import TempSalesBooking, SalesBooking, Motorcycle
from payments.models import Payment
from ..test_helpers.model_factories import (
    InventorySettingsFactory,
    MotorcycleFactory,
    UserFactory,
)
from payments.webhook_handlers.sales_handlers import handle_sales_booking_succeeded

@skipIf(not settings.STRIPE_SECRET_KEY, "Stripe API key not configured in settings")
@override_settings(ADMIN_EMAIL='ethan.betts.dev@gmail.com')
class TestConcurrencyCases(TestCase):
    def setUp(self):
        self.settings = InventorySettingsFactory(
            enable_reservation_by_deposit=True,
            deposit_amount=Decimal('250.00'),
            currency_code='AUD'
        )
        self.motorcycle = MotorcycleFactory(
            is_available=True,
            price=Decimal('18000.00'),
            status='available',
        )
        stripe.api_key = settings.STRIPE_SECRET_KEY

    def test_concurrent_booking_race_condition(self):
        # 1. Set up two separate clients for two different users
        user_a = UserFactory(username='user_a', email='usera@example.com')
        client_a = Client()
        client_a.force_login(user_a)

        user_b = UserFactory(username='user_b', email='userb@example.com')
        client_b = Client()
        client_b.force_login(user_b)

        # 2. Both users go through the booking flow up to the payment page
        # This simulates them acting concurrently before any final payment is made.
        
        # User A's flow
        client_a.post(reverse('inventory:initiate_booking', kwargs={'pk': self.motorcycle.pk}), {'deposit_required_for_flow': 'true'})
        client_a.post(reverse('inventory:step1_sales_profile'), {'name': 'User A', 'email': 'usera@example.com', 'phone_number': '111-1111'})
        client_a.post(reverse('inventory:step2_booking_details_and_appointment'), {'request_viewing': 'no', 'terms_accepted': 'on'})
        client_a.get(reverse('inventory:step3_payment'))
        
        # User B's flow
        client_b.post(reverse('inventory:initiate_booking', kwargs={'pk': self.motorcycle.pk}), {'deposit_required_for_flow': 'true'})
        client_b.post(reverse('inventory:step1_sales_profile'), {'name': 'User B', 'email': 'userb@example.com', 'phone_number': '222-2222'})
        client_b.post(reverse('inventory:step2_booking_details_and_appointment'), {'request_viewing': 'no', 'terms_accepted': 'on'})
        client_b.get(reverse('inventory:step3_payment'))

        # At this point, we should have two TempSalesBookings and two Payment objects
        self.assertEqual(TempSalesBooking.objects.count(), 2)
        self.assertEqual(Payment.objects.count(), 2)
        
        payment_obj_a = Payment.objects.get(temp_sales_booking__sales_profile__email='usera@example.com')
        payment_obj_b = Payment.objects.get(temp_sales_booking__sales_profile__email='userb@example.com')

        # ** THE FIX IS HERE **
        # Store the expected sales profile *before* the temp booking is deleted.
        expected_sales_profile = payment_obj_a.temp_sales_booking.sales_profile

        # 3. Simulate the "race": User A's payment is processed first.
        try:
            intent_a = stripe.PaymentIntent.confirm(payment_obj_a.stripe_payment_intent_id, payment_method="pm_card_visa", return_url='http://test.com/a')
        except stripe.error.StripeError as e:
            self.fail(f"Stripe API call for User A failed during test: {e}")
        
        # Manually call the webhook handler for User A, which should succeed.
        handle_sales_booking_succeeded(payment_obj_a, intent_a)

        # 4. Assert that User A successfully booked the motorcycle.
        self.assertEqual(SalesBooking.objects.count(), 1, "Only one SalesBooking should be created.")
        final_booking = SalesBooking.objects.first()
        
        # Use the stored profile for the assertion.
        self.assertEqual(final_booking.sales_profile, expected_sales_profile)
        
        self.motorcycle.refresh_from_db()
        self.assertFalse(self.motorcycle.is_available, "Motorcycle should be marked as unavailable after User A's booking.")

        # 5. Now, simulate User B's payment being processed.
        try:
            intent_b = stripe.PaymentIntent.confirm(payment_obj_b.stripe_payment_intent_id, payment_method="pm_card_visa", return_url='http://test.com/b')
        except stripe.error.StripeError as e:
            self.fail(f"Stripe API call for User B failed during test: {e}")

        # Manually call the webhook handler for User B.
        # A robust handler should check for motorcycle availability and fail gracefully.
        handle_sales_booking_succeeded(payment_obj_b, intent_b)

        # 6. Assert that User B's booking FAILED.
        self.assertEqual(SalesBooking.objects.count(), 1, "SalesBooking count should still be 1 after User B's failed attempt.")
