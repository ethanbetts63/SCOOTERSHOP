from django.test import TestCase
from datetime import date, time
from decimal import Decimal
import datetime
import uuid
from django.db import models

from inventory.models import TempSalesBooking
from inventory.models.temp_sales_booking import (
    PAYMENT_STATUS_CHOICES,
)



from inventory.tests.test_helpers.model_factories import (
    TempSalesBookingFactory,
    SalesProfileFactory,
    MotorcycleFactory,
)
from payments.tests.test_helpers.model_factories import PaymentFactory


class TempSalesBookingModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.motorcycle = MotorcycleFactory()
        cls.sales_profile = SalesProfileFactory()
        cls.payment = PaymentFactory()

        cls.temp_sales_booking = TempSalesBookingFactory(
            motorcycle=cls.motorcycle,
            sales_profile=cls.sales_profile,
            payment=cls.payment,
        )

    def test_temp_sales_booking_creation(self):
        self.assertIsInstance(self.temp_sales_booking, TempSalesBooking)
        self.assertIsNotNone(self.temp_sales_booking.pk)
        self.assertEqual(TempSalesBookingFactory._meta.model.objects.count(), 1)

    def test_motorcycle_foreign_key(self):
        field = self.temp_sales_booking._meta.get_field("motorcycle")
        self.assertEqual(field.related_model, self.motorcycle.__class__)
        self.assertEqual(field.remote_field.on_delete, models.SET_NULL)
        self.assertTrue(field.null)
        self.assertTrue(field.blank)
        self.assertEqual(self.temp_sales_booking.motorcycle, self.motorcycle)
        self.assertEqual(
            field.help_text,
            "The motorcycle associated with this temporary sales booking.",
        )

        self.temp_sales_booking.motorcycle = None
        self.temp_sales_booking.save()
        self.assertIsNone(self.temp_sales_booking.motorcycle)

    def test_sales_profile_foreign_key(self):
        field = self.temp_sales_booking._meta.get_field("sales_profile")
        self.assertEqual(field.related_model, self.sales_profile.__class__)
        self.assertEqual(field.remote_field.on_delete, models.CASCADE)
        self.assertTrue(field.null)
        self.assertTrue(field.blank)
        self.assertEqual(self.temp_sales_booking.sales_profile, self.sales_profile)
        self.assertEqual(
            field.help_text, "The customer's sales profile for this temporary booking."
        )

        self.temp_sales_booking.sales_profile = None
        self.temp_sales_booking.save()
        self.assertIsNone(self.temp_sales_booking.sales_profile)

    def test_payment_one_to_one_field(self):
        field = self.temp_sales_booking._meta.get_field("payment")
        self.assertEqual(field.related_model, self.payment.__class__)
        self.assertEqual(field.remote_field.on_delete, models.SET_NULL)
        self.assertTrue(field.null)
        self.assertTrue(field.blank)
        self.assertEqual(self.temp_sales_booking.payment, self.payment)
        self.assertEqual(
            field.help_text,
            "Link to the associated payment record, if any (e.g., for deposit).",
        )

        self.temp_sales_booking.payment = None
        self.temp_sales_booking.save()
        self.assertIsNone(self.temp_sales_booking.payment)

    def test_amount_paid_field(self):
        new_booking_default_amount = TempSalesBookingFactory(
            motorcycle=self.motorcycle,
            sales_profile=self.sales_profile,
        )

        field = new_booking_default_amount._meta.get_field("amount_paid")
        self.assertIsInstance(new_booking_default_amount.amount_paid, Decimal)
        self.assertEqual(field.max_digits, 10)
        self.assertEqual(field.decimal_places, 2)
        self.assertEqual(new_booking_default_amount.amount_paid, Decimal("0.00"))
        self.assertEqual(
            field.help_text,
            "The amount paid for this booking (e.g., deposit amount). Defaults to 0.",
        )

    def test_payment_status_field(self):
        field = self.temp_sales_booking._meta.get_field("payment_status")
        self.assertIsInstance(self.temp_sales_booking.payment_status, str)
        self.assertEqual(field.max_length, 20)
        self.assertEqual(field.choices, PAYMENT_STATUS_CHOICES)
        self.assertEqual(field.default, "unpaid")
        self.assertIn(
            self.temp_sales_booking.payment_status,
            [choice[0] for choice in PAYMENT_STATUS_CHOICES],
        )
        self.assertEqual(
            field.help_text,
            "Current payment status of the temporary booking (e.g., unpaid, deposit_paid).",
        )

    def test_currency_field(self):
        field = self.temp_sales_booking._meta.get_field("currency")
        self.assertIsInstance(self.temp_sales_booking.currency, str)
        self.assertEqual(field.max_length, 3)
        self.assertEqual(field.default, "AUD")
        self.assertEqual(
            field.help_text,
            "The three-letter ISO currency code for the booking (e.g., AUD).",
        )

    def test_stripe_payment_intent_id_field(self):
        field = self.temp_sales_booking._meta.get_field("stripe_payment_intent_id")
        self.assertIsInstance(
            self.temp_sales_booking.stripe_payment_intent_id, (str, type(None))
        )
        self.assertEqual(field.max_length, 100)
        self.assertTrue(field.unique)
        self.assertTrue(field.blank)
        self.assertTrue(field.null)
        self.assertEqual(
            field.help_text,
            "The ID of the Stripe Payment Intent associated with this booking, if applicable.",
        )

        unique_id = f"pi_{uuid.uuid4().hex[:24]}"
        TempSalesBookingFactory(
            motorcycle=self.motorcycle,
            sales_profile=self.sales_profile,
            stripe_payment_intent_id=unique_id,
        )
        with self.assertRaises(Exception):
            TempSalesBookingFactory(
                motorcycle=self.motorcycle,
                sales_profile=self.sales_profile,
                stripe_payment_intent_id=unique_id,
            )

    def test_appointment_date_field(self):
        field = self.temp_sales_booking._meta.get_field("appointment_date")
        self.assertIsInstance(
            self.temp_sales_booking.appointment_date, (date, type(None))
        )
        self.assertTrue(field.null)
        self.assertTrue(field.blank)
        self.assertEqual(
            field.help_text, "Requested date for the test drive or appointment."
        )

    def test_appointment_time_field(self):
        field = self.temp_sales_booking._meta.get_field("appointment_time")
        self.assertIsInstance(
            self.temp_sales_booking.appointment_time, (time, type(None))
        )
        self.assertTrue(field.null)
        self.assertTrue(field.blank)
        self.assertEqual(
            field.help_text, "Requested time for the test drive or appointment."
        )

    def test_customer_notes_field(self):
        field = self.temp_sales_booking._meta.get_field("customer_notes")
        self.assertIsInstance(self.temp_sales_booking.customer_notes, (str, type(None)))
        self.assertTrue(field.blank)
        self.assertTrue(field.null)
        self.assertEqual(
            field.help_text,
            "Any additional notes or messages provided by the customer during the process.",
        )

    def test_created_at_field(self):
        field = self.temp_sales_booking._meta.get_field("created_at")
        self.assertIsInstance(self.temp_sales_booking.created_at, datetime.datetime)
        self.assertTrue(field.auto_now_add)
        self.assertEqual(
            field.help_text,
            "The date and time when this temporary booking was created.",
        )

    def test_updated_at_field(self):
        field = self.temp_sales_booking._meta.get_field("updated_at")
        self.assertIsInstance(self.temp_sales_booking.updated_at, datetime.datetime)
        self.assertTrue(field.auto_now)
        self.assertEqual(
            field.help_text,
            "The date and time when this temporary booking was last updated.",
        )

        old_updated_at = self.temp_sales_booking.updated_at
        self.temp_sales_booking.customer_notes = "Updated temp notes"
        self.temp_sales_booking.save()
        self.assertGreater(self.temp_sales_booking.updated_at, old_updated_at)

    def test_meta_options(self):
        self.assertEqual(TempSalesBookingFactory._meta.model._meta.verbose_name, "Temporary Sales Booking")
        self.assertEqual(
            TempSalesBookingFactory._meta.model._meta.verbose_name_plural, "Temporary Sales Bookings"
        )
        self.assertEqual(TempSalesBookingFactory._meta.model._meta.ordering, ["-created_at"])
