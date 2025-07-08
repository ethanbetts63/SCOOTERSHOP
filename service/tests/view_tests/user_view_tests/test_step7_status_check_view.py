from django.test import TestCase
from django.urls import reverse
import uuid
from unittest.mock import patch

from service.models import ServiceBooking
from payments.models import Payment
from ...test_helpers.model_factories import (
    UserFactory,
    ServiceBookingFactory,
    PaymentFactory,
)


class Step7StatusCheckViewTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.base_url = reverse("service:service_booking_status_check")

    def setUp(self):
        self.client.force_login(self.user)
        ServiceBooking.objects.all().delete()
        Payment.objects.all().delete()

    def test_get_status_ready(self):

        payment_intent_id = f"pi_{uuid.uuid4().hex}"
        booking = ServiceBookingFactory(stripe_payment_intent_id=payment_intent_id)

        url = f"{self.base_url}?payment_intent_id={payment_intent_id}"
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data["status"], "ready")
        self.assertEqual(data["booking_reference"], booking.service_booking_reference)
        self.assertEqual(data["booking_status"], booking.get_booking_status_display())

        self.assertEqual(
            self.client.session.get("service_booking_reference"),
            booking.service_booking_reference,
        )

    def test_get_status_processing(self):

        payment_intent_id = f"pi_{uuid.uuid4().hex}"

        PaymentFactory(stripe_payment_intent_id=payment_intent_id)

        url = f"{self.base_url}?payment_intent_id={payment_intent_id}"
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data["status"], "processing")
        self.assertEqual(data["message"], "Booking finalization is still in progress.")

    def test_get_status_error_finalization_failed(self):

        payment_intent_id = f"pi_{uuid.uuid4().hex}"

        url = f"{self.base_url}?payment_intent_id={payment_intent_id}"
        response = self.client.get(url)

        self.assertEqual(response.status_code, 500)
        data = response.json()

        self.assertEqual(data["status"], "error")
        self.assertEqual(
            data["message"],
            "Booking finalization failed. Please contact support for assistance.",
        )

    def test_get_missing_payment_intent_id(self):

        response = self.client.get(self.base_url)

        self.assertEqual(response.status_code, 400)
        data = response.json()

        self.assertEqual(data["status"], "error")
        self.assertEqual(data["message"], "Payment Intent ID is required.")

    @patch(
        "service.views.user_views.step7_status_check_view.ServiceBooking.objects.get"
    )
    def test_get_generic_exception_returns_500(self, mock_get):

        payment_intent_id = f"pi_{uuid.uuid4().hex}"
        mock_get.side_effect = Exception("A database error occurred")

        url = f"{self.base_url}?payment_intent_id={payment_intent_id}"
        response = self.client.get(url)

        self.assertEqual(response.status_code, 500)
        data = response.json()

        self.assertEqual(data["status"], "error")
        self.assertIn("An internal server error occurred", data["message"])
