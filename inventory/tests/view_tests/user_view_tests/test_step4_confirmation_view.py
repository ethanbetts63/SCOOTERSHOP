from django.test import TestCase
from django.urls import reverse
from django.contrib.messages import get_messages
from decimal import Decimal
from inventory.tests.test_helpers.model_factories import (
    SalesBookingFactory,
    PaymentFactory,
    MotorcycleFactory,
)


class Step4ConfirmationViewTest(TestCase):
    def setUp(self):
        self.motorcycle = MotorcycleFactory(price=Decimal("10000.00"))
        self.sales_booking = SalesBookingFactory(
            motorcycle=self.motorcycle,
            amount_paid=Decimal("200.00"),
            stripe_payment_intent_id="pi_valid_booking_123",
        )
        self.base_url = reverse("inventory:step4_confirmation")

    def test_confirmation_view_with_valid_session_reference(self):
        session = self.client.session
        session["current_sales_booking_reference"] = (
            self.sales_booking.sales_booking_reference
        )
        session["temp_sales_booking_uuid"] = "some-uuid-to-be-deleted"
        session.save()

        response = self.client.get(self.base_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "inventory/step4_confirmation.html")
        self.assertIn("sales_booking", response.context)
        self.assertEqual(response.context["sales_booking"], self.sales_booking)
        self.assertFalse(response.context["is_processing"])
        self.assertEqual(response.context["amount_owing"], Decimal("9800.00"))

        self.assertNotIn("temp_sales_booking_uuid", self.client.session)

    def test_confirmation_view_with_valid_payment_intent_id(self):
        url = f"{self.base_url}?payment_intent_id={self.sales_booking.stripe_payment_intent_id}"
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "inventory/step4_confirmation.html")
        self.assertIn("sales_booking", response.context)
        self.assertEqual(response.context["sales_booking"], self.sales_booking)
        self.assertFalse(response.context["is_processing"])

        self.assertEqual(
            self.client.session["current_sales_booking_reference"],
            self.sales_booking.sales_booking_reference,
        )

    def test_confirmation_view_in_processing_state(self):
        payment_intent_id = "pi_processing_456"
        PaymentFactory(stripe_payment_intent_id=payment_intent_id)

        url = f"{self.base_url}?payment_intent_id={payment_intent_id}"
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "inventory/step4_confirmation.html")
        self.assertTrue(response.context["is_processing"])
        self.assertEqual(response.context["payment_intent_id"], payment_intent_id)
        self.assertNotIn("sales_booking", response.context)

    def test_confirmation_view_no_booking_or_payment_found_redirects(self):
        url = f"{self.base_url}?payment_intent_id=pi_does_not_exist_789"
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("inventory:used"))

        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(
            str(messages[0]),
            "Could not find a booking confirmation. Please start over if you have not booked.",
        )

    def test_confirmation_view_no_session_or_params_redirects(self):
        response = self.client.get(self.base_url)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("inventory:used"))

        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(
            str(messages[0]),
            "Could not find a booking confirmation. Please start over if you have not booked.",
        )

    def test_confirmation_view_with_invalid_session_reference(self):
        session = self.client.session
        session["current_sales_booking_reference"] = "INVALID-REF-123"
        session.save()

        response = self.client.get(self.base_url)

        self.assertNotIn("current_sales_booking_reference", self.client.session)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("inventory:used"))
