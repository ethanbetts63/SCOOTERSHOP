import datetime
from decimal import Decimal
import stripe
from unittest import skipIf
from django.test import TestCase, Client
from django.urls import reverse
from django.conf import settings
from inventory.models import SalesBooking
from payments.models import Payment
from ..test_helpers.model_factories import (
    InventorySettingsFactory,
    MotorcycleFactory,
    UserFactory,
    SalesTermsFactory,
)
from payments.webhook_handlers.sales_handlers import handle_sales_booking_succeeded

@skipIf(not settings.STRIPE_SECRET_KEY, "Stripe API key not configured in settings")
class TestAnonymousDepositFlowWithUpdates(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = UserFactory()
        self.client.force_login(self.user)
        self.settings = InventorySettingsFactory(
            enable_reservation_by_deposit=True,
            deposit_amount=Decimal("150.00"),
            currency_code="AUD",
        )
        self.motorcycle = MotorcycleFactory(
            price=Decimal("12000.00"),
            status="for_sale",
            year=1999,
            brand="Kawasaki",
            model="Star",
        )
        self.another_motorcycle = MotorcycleFactory(
            price=Decimal("15000.00"),
            status="for_sale",
            year=2022,
            brand="Ducati",
            model="Panigale",
        )
        self.sales_terms = SalesTermsFactory(is_active=True)
        stripe.api_key = settings.STRIPE_SECRET_KEY

    def test_anonymous_deposit_flow_with_updates(self):
        anon_client = Client()
        initiate_url = reverse(
            "inventory:initiate_booking", kwargs={"pk": self.motorcycle.pk}
        )
        anon_client.post(initiate_url, {"deposit_required_for_flow": "true"})

        self.assertIn("temp_sales_booking_uuid", anon_client.session)

        step1_url = reverse("inventory:step1_sales_profile")
        step2_url = reverse("inventory:step2_booking_details_and_appointment")
        step3_url = reverse("inventory:step3_payment")

        profile_data = {
            "name": "Guest User",
            "email": "guest.user@example.com",
            "phone_number": "555-5678",
        }
        anon_client.post(step1_url, profile_data)

        response = anon_client.get(step1_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "guest.user@example.com", count=2)

        updated_profile_data = {
            "name": "Guest User",
            "email": "guest.user@example.com",
            "phone_number": "555-9999",
        }
        anon_client.post(step1_url, updated_profile_data)

        appointment_data = {
            "appointment_date": "2025-09-16",
            "appointment_time": "11:00",
            "terms_accepted": "on",
        }
        anon_client.post(step2_url, appointment_data)

        response = anon_client.get(step2_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "2025-09-16", count=1)

        updated_appointment_data = {
            "appointment_date": "2025-09-16",
            "appointment_time": "15:30",
            "terms_accepted": "on",
        }
        anon_client.post(step2_url, updated_appointment_data)

        anon_client.get(step3_url)
        payment_obj = Payment.objects.first()
        payment_obj.refresh_from_db()
        payment_intent_id = payment_obj.stripe_payment_intent_id

        try:
            confirmation_url_path = reverse("inventory:step4_confirmation")
            full_return_url = f"http://testserver{confirmation_url_path}"
            stripe.PaymentIntent.confirm(
                payment_intent_id,
                payment_method="pm_card_visa",
                return_url=full_return_url,
            )
        except stripe.error.StripeError as e:
            self.fail(f"Stripe API call failed during test: {e}")

        updated_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        handle_sales_booking_succeeded(payment_obj, updated_intent)

        self.assertEqual(SalesBooking.objects.count(), 1)
        final_booking = SalesBooking.objects.first()
        self.assertEqual(final_booking.payment_status, "deposit_paid")

        self.assertEqual(final_booking.sales_profile.name, "Guest User")
        self.assertEqual(final_booking.sales_profile.phone_number, "555-9999")
        self.assertEqual(final_booking.appointment_time, datetime.time(15, 30))
        self.assertIsNone(final_booking.sales_profile.user)

        self.motorcycle.refresh_from_db()
        self.assertFalse(self.motorcycle.is_available)