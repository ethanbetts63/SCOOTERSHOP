import datetime
from decimal import Decimal
import stripe
from unittest import skipIf

from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.conf import settings

from inventory.models import TempSalesBooking, SalesBooking
from payments.models import Payment
from inventory.tests.test_helpers.model_factories import InventorySettingsFactory, MotorcycleFactory, SalesTermsFactory
from users.tests.test_helpers.model_factories import UserFactory
from payments.webhook_handlers.sales_handlers import handle_sales_booking_succeeded


@skipIf(not settings.STRIPE_SECRET_KEY, "Stripe API key not configured in settings")
class TestLoggedInUserSwitchesBikeMidFlow(TestCase):
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

    def test_logged_in_user_switches_bike_mid_flow(self):
        step1_url = reverse("inventory:step1_sales_profile")
        step2_url = reverse("inventory:step2_booking_details_and_appointment")
        step3_url = reverse("inventory:step3_payment")

        initiate_url_1 = reverse(
            "inventory:initiate_booking", kwargs={"pk": self.motorcycle.pk}
        )
        self.client.post(initiate_url_1, {"deposit_required_for_flow": "true"})

        updated_profile_data = {
            "name": "Thorough Tester Updated",
            "email": "thorough.tester@example.com",
            "phone_number": "555-4321",
        }
        self.client.post(step1_url, updated_profile_data)

        updated_appointment_data = {
            "appointment_date": "2025-09-20",
            "appointment_time": "09:00",
            "terms_accepted": "on",
        }
        self.client.post(step2_url, updated_appointment_data)

        self.client.get(step3_url)

        initiate_url_2 = reverse(
            "inventory:initiate_booking", kwargs={"pk": self.another_motorcycle.pk}
        )
        self.client.post(initiate_url_2, {"deposit_required_for_flow": "true"})

        response = self.client.get(step1_url) 
        self.assertContains(response, "Thorough Tester Updated")
        self.client.post(step1_url, updated_profile_data)

        new_appointment_data = {
            "appointment_date": "2025-11-01",
            "appointment_time": "10:00",
            "terms_accepted": "on",
        }
        self.client.post(step2_url, new_appointment_data)

        self.client.get(step3_url)
        temp_booking = TempSalesBooking.objects.get(
            session_uuid=self.client.session["temp_sales_booking_uuid"]
        )
        payment_obj = Payment.objects.get(temp_sales_booking=temp_booking)
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
        final_booking = SalesBooking.objects.get(motorcycle=self.another_motorcycle)
        self.assertEqual(final_booking.payment_status, "deposit_paid")

        self.assertEqual(final_booking.motorcycle, self.another_motorcycle)
        self.assertEqual(final_booking.sales_profile.name, "Thorough Tester Updated")
        self.assertEqual(final_booking.appointment_date, datetime.date(2025, 11, 1))

        self.motorcycle.refresh_from_db()
        self.assertTrue(
            self.motorcycle.is_available,
            "Original motorcycle should not have been reserved.",
        )

        self.another_motorcycle.refresh_from_db()
        self.assertFalse(
            self.another_motorcycle.is_available,
            "Second motorcycle should be reserved.",
        )