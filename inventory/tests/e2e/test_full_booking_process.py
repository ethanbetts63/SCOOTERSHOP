import datetime
from decimal import Decimal
import stripe
from unittest import skipIf

from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.conf import settings

from inventory.models import TempSalesBooking, SalesBooking
from payments.models import Payment
from unittest.mock import patch, MagicMock

from ..test_helpers.model_factories import (
    InventorySettingsFactory,
    MotorcycleFactory,
    UserFactory,
    SalesTermsFactory,
)
from payments.webhook_handlers.sales_handlers import handle_sales_booking_succeeded


@override_settings(ADMIN_EMAIL="ethan.betts.dev@gmail.com")
class TestEnquiryFlows(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = UserFactory()
        self.client.force_login(self.user)
        self.settings = InventorySettingsFactory(currency_code="AUD")
        self.motorcycle = MotorcycleFactory(
            is_available=True,
            status="available",
            price=Decimal("5000.00"),
            year=1993,
            brand="Kawasaki",
            model="Enough",
        )
        self.another_motorcycle = MotorcycleFactory(
            is_available=True, status="available", price=Decimal("8000.00")
        )
        self.sales_terms = SalesTermsFactory(is_active=True)

    def test_enquiry_with_appointment_flow(self):
        initiate_url = reverse(
            "inventory:initiate_booking", kwargs={"pk": self.motorcycle.pk}
        )
        response = self.client.post(
            initiate_url, {"deposit_required_for_flow": "false"}, follow=True
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("temp_sales_booking_uuid", self.client.session)

        step1_url = reverse("inventory:step1_sales_profile")
        step2_url = reverse("inventory:step2_booking_details_and_appointment")

        profile_data = {
            "name": "Enquiry User",
            "email": "enquiry@example.com",
            "phone_number": "555-0000",
        }
        response = self.client.post(step1_url, profile_data)
        self.assertRedirects(response, step2_url)

        self.client.get(step1_url)
        updated_profile_data = {
            "name": "Enquiry User Updated",
            "email": "enquiry@example.com",
            "phone_number": "555-1111",
        }
        response = self.client.post(step1_url, updated_profile_data)
        self.assertRedirects(response, step2_url)

        appointment_data = {
            "appointment_date": "2025-10-20",
            "appointment_time": "10:00",
            "terms_accepted": "on",
            "customer_notes": "I would like to come see this bike.",
        }
        response = self.client.post(step2_url, appointment_data)

        self.assertRedirects(response, reverse("inventory:step4_confirmation"))
        self.assertEqual(TempSalesBooking.objects.count(), 0)
        self.assertEqual(SalesBooking.objects.count(), 1)

        final_booking = SalesBooking.objects.first()
        self.assertEqual(final_booking.sales_profile.name, "Enquiry User Updated")
        self.assertEqual(final_booking.sales_profile.phone_number, "555-1111")
        self.assertEqual(final_booking.payment_status, "unpaid")
        self.assertIsNotNone(final_booking.appointment_date)

        confirmation_response = self.client.get(response.url)
        self.assertEqual(confirmation_response.status_code, 200)
        self.assertContains(
            confirmation_response, final_booking.sales_booking_reference
        )
        self.assertIn("last_sales_booking_timestamp", self.client.session)

    


@skipIf(not settings.STRIPE_SECRET_KEY, "Stripe API key not configured in settings")
class TestDepositFlows(TestCase):
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

    def test_logged_in_deposit_flow_with_updates(self, mock_stripe_modify, mock_stripe_retrieve, mock_stripe_create):
        # Mock Stripe API calls
        mock_stripe_create.return_value = MagicMock(id='pi_test_create', client_secret='cs_test_create', status='requires_payment_method', amount=15000, currency='aud')
        mock_stripe_retrieve.return_value = MagicMock(id='pi_test_retrieve', client_secret='cs_test_retrieve', status='succeeded', amount=15000, currency='aud')
        mock_stripe_modify.return_value = MagicMock(id='pi_test_modify', client_secret='cs_test_modify', status='requires_payment_method', amount=15000, currency='aud')

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

        # Mock the confirm call as well
        with patch('inventory.utils.create_update_sales_payment_intent.stripe.PaymentIntent.confirm') as mock_stripe_confirm:
            mock_stripe_confirm.return_value = MagicMock(id=payment_intent_id, status='succeeded', amount=15000, currency='aud')
            
            confirmation_url_path = reverse("inventory:step4_confirmation")
            full_return_url = f"http://testserver{confirmation_url_path}"
            stripe.PaymentIntent.confirm(
                payment_intent_id,
                payment_method="pm_card_visa",
                return_url=full_return_url,
            )

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
