from django.test import TestCase, Client
from django.urls import reverse
from decimal import Decimal
import datetime




from ..test_helpers.model_factories import (
    MotorcycleFactory,
    SalesProfileFactory,
    PaymentFactory,
    SalesBookingFactory,
)


class AjaxGetPaymentStatusTest(TestCase):

    @classmethod
    def setUpTestData(cls):

        cls.client = Client()

        cls.motorcycle = MotorcycleFactory()
        cls.sales_profile = SalesProfileFactory()

        cls.successful_payment = PaymentFactory(
            status="succeeded", amount=Decimal("100.00"), currency="AUD"
        )
        cls.successful_booking = SalesBookingFactory(
            motorcycle=cls.motorcycle,
            sales_profile=cls.sales_profile,
            payment=cls.successful_payment,
            stripe_payment_intent_id=cls.successful_payment.stripe_payment_intent_id,
            amount_paid=cls.successful_payment.amount,
            payment_status="paid",
            booking_status="confirmed",
            appointment_date=datetime.date.today(),
            appointment_time=datetime.time(10, 0, 0),
        )

        cls.processing_payment = PaymentFactory(
            status="succeeded", amount=Decimal("50.00"), currency="AUD"
        )

        cls.non_existent_payment_intent_id = "pi_nonexistent12345"

    def test_successful_payment_status_check(self):

        response = self.client.get(
            reverse("inventory:ajax_sales_payment_status_check"),
            {"payment_intent_id": self.successful_booking.stripe_payment_intent_id},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data["status"], "ready")
        self.assertEqual(
            data["booking_reference"], self.successful_booking.sales_booking_reference
        )
        self.assertEqual(data["booking_status"], "Confirmed")
        self.assertEqual(data["payment_status"], "paid")
        self.assertEqual(
            Decimal(data["amount_paid"]), self.successful_booking.amount_paid
        )
        self.assertEqual(data["currency"], self.successful_booking.currency)
        self.assertIn(str(self.motorcycle.year), data["motorcycle_details"])
        self.assertIn(self.motorcycle.brand, data["motorcycle_details"])
        self.assertIn(self.motorcycle.model, data["motorcycle_details"])
        self.assertEqual(data["customer_name"], self.sales_profile.name)
        self.assertEqual(
            data["appointment_date"],
            self.successful_booking.appointment_date.strftime("%d %b %Y"),
        )
        self.assertEqual(
            data["appointment_time"],
            self.successful_booking.appointment_time.strftime("%I:%M %p"),
        )

        self.assertIn("sales_booking_reference", self.client.session)
        self.assertEqual(
            self.client.session["sales_booking_reference"],
            self.successful_booking.sales_booking_reference,
        )

    def test_payment_processing_status(self):

        response = self.client.get(
            reverse("inventory:ajax_sales_payment_status_check"),
            {"payment_intent_id": self.processing_payment.stripe_payment_intent_id},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data["status"], "processing")
        self.assertIn("Booking finalization is still in progress.", data["message"])

    def test_payment_intent_not_found(self):

        response = self.client.get(
            reverse("inventory:ajax_sales_payment_status_check"),
            {"payment_intent_id": self.non_existent_payment_intent_id},
        )
        self.assertEqual(response.status_code, 500)
        data = response.json()

        self.assertEqual(data["status"], "error")
        self.assertIn(
            "Booking finalization failed. Please contact support for assistance.",
            data["message"],
        )

    def test_missing_payment_intent_id(self):

        response = self.client.get(reverse("inventory:ajax_sales_payment_status_check"))
        self.assertEqual(response.status_code, 400)
        data = response.json()

        self.assertEqual(data["status"], "error")
        self.assertEqual(data["message"], "Payment Intent ID is required.")

    def test_sales_booking_details_in_response(self):

        response = self.client.get(
            reverse("inventory:ajax_sales_payment_status_check"),
            {"payment_intent_id": self.successful_booking.stripe_payment_intent_id},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertIn("booking_reference", data)
        self.assertIn("booking_status", data)
        self.assertIn("payment_status", data)
        self.assertIn("amount_paid", data)
        self.assertIn("currency", data)
        self.assertIn("motorcycle_details", data)
        self.assertIn("customer_name", data)
        self.assertIn("appointment_date", data)
        self.assertIn("appointment_time", data)

        self.assertEqual(
            data["booking_reference"], self.successful_booking.sales_booking_reference
        )
        self.assertEqual(
            data["booking_status"], self.successful_booking.get_booking_status_display()
        )
        self.assertEqual(
            data["payment_status"], self.successful_booking.get_payment_status_display()
        )
        self.assertEqual(
            Decimal(data["amount_paid"]), self.successful_booking.amount_paid
        )
        self.assertEqual(data["currency"], self.successful_booking.currency)
        self.assertEqual(
            data["motorcycle_details"],
            f"{self.successful_booking.motorcycle.year} {self.successful_booking.motorcycle.brand} {self.successful_booking.motorcycle.model}",
        )
        self.assertEqual(
            data["customer_name"], self.successful_booking.sales_profile.name
        )
        self.assertEqual(
            data["appointment_date"],
            self.successful_booking.appointment_date.strftime("%d %b %Y"),
        )
        self.assertEqual(
            data["appointment_time"],
            self.successful_booking.appointment_time.strftime("%I:%M %p"),
        )
