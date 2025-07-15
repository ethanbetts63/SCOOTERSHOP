import datetime
from decimal import Decimal
import stripe
from unittest import skipIf
from django.test import TestCase, Client
from django.urls import reverse
from django.conf import settings
from inventory.models import  SalesBooking
from payments.models import Payment
from ..test_helpers.model_factories import (
    InventorySettingsFactory,
    MotorcycleFactory,
    UserFactory,
    SalesTermsFactory,
)
from payments.webhook_handlers.sales_handlers import handle_sales_booking_succeeded

@skipIf(not settings.STRIPE_SECRET_KEY, "Stripe API key not configured in settings")
class TestLoggedInDepositFlowWithUpdates(TestCase):
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
            is_available=True,
            price=Decimal("12000.00"),
            status="available",
            year=1999,
            brand="Kawasaki",
            model="Star",
        )
        self.another_motorcycle = MotorcycleFactory(
            is_available=True,
            price=Decimal("15000.00"),
            status="available",
            year=2022,
            brand="Ducati",
            model="Panigale",
        )
        self.sales_terms = SalesTermsFactory(is_active=True)
        stripe.api_key = settings.STRIPE_SECRET_KEY

    def test_logged_in_deposit_flow_with_updates(self):
        initiate_url = reverse(
            "inventory:initiate_booking", kwargs={"pk": self.motorcycle.pk}
        )
        self.client.post(initiate_url, {"deposit_required_for_flow": "true"})

        step1_url = reverse("inventory:step1_sales_profile")
        step2_url = reverse("inventory:step2_booking_details_and_appointment")
        step3_url = reverse("inventory:step3_payment")

        profile_data = {
            "name": "Thorough Tester",
            "email": "thorough.tester@example.com",
            "phone_number": "555-1234",
        }
        self.client.post(step1_url, profile_data)
        self.client.get(step1_url)
        updated_profile_data = {
            "name": "Thorough Tester Updated",
            "email": "thorough.tester@example.com",
            "phone_number": "555-4321",
        }
        self.client.post(step1_url, updated_profile_data)

        appointment_data = {
            "appointment_date": "2025-09-15",
            "appointment_time": "14:00",
            "terms_accepted": "on",
        }
        self.client.post(step2_url, appointment_data)
        self.client.get(step2_url)
        updated_appointment_data = {
            "appointment_date": "2025-09-20",
            "appointment_time": "09:00",
            "terms_accepted": "on",
        }
        self.client.post(step2_url, updated_appointment_data)

        self.client.get(step3_url)
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

        final_booking = SalesBooking.objects.first()
        self.assertEqual(final_booking.payment_status, "deposit_paid")

        self.assertEqual(final_booking.sales_profile.name, "Thorough Tester Updated")
        self.assertEqual(final_booking.sales_profile.phone_number, "555-4321")
        
        self.assertEqual(final_booking.appointment_date, datetime.date(2025, 9, 20))
        self.assertEqual(final_booking.appointment_time, datetime.time(9, 0))

        self.motorcycle.refresh_from_db()
        self.assertFalse(self.motorcycle.is_available)

        another_user_client = Client()
        another_user = UserFactory(username="another_user")
        another_user_client.force_login(another_user)
        details_url = reverse(
            "inventory:motorcycle-detail", kwargs={"pk": self.motorcycle.pk}
        )
        initiate_blocked_url = reverse(
            "inventory:initiate_booking", kwargs={"pk": self.motorcycle.pk}
        )
        response_blocked = another_user_client.post(initiate_blocked_url, follow=True)
        self.assertRedirects(
            response_blocked, details_url, status_code=302, target_status_code=200
        )
