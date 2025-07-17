from django.test import TestCase
from datetime import date, time
from decimal import Decimal
import datetime
import uuid
from django.db import models
from inventory.models import SalesBooking
from inventory.models.sales_booking import (
    PAYMENT_STATUS_CHOICES,
    BOOKING_STATUS_CHOICES,
)
from inventory.forms.admin_motorcycle_form import MotorcycleForm
from users.tests.test_helpers.model_factories import UserFactory, StaffUserFactory
from service.tests.test_helpers.model_factories import ServiceBookingFactory, ServiceProfileFactory, ServiceTypeFactory, ServiceSettingsFactory, ServiceTermsFactory, ServicefaqFactory, CustomerMotorcycleFactory, BlockedServiceDateFactory, ServiceBrandFactory
from inventory.tests.test_helpers.model_factories import SalesBookingFactory, SalesProfileFactory, MotorcycleConditionFactory, MotorcycleFactory, MotorcycleImageFactory, FeaturedMotorcycleFactory, InventorySettingsFactory, BlockedSalesDateFactory
from payments.tests.test_helpers.model_factories import PaymentFactory, WebhookEventFactory
from refunds.tests.test_helpers.model_factories import RefundRequestFactory, RefundSettingsFactory


class SalesBookingModelTest(TestCase):

    @classmethod
    def setUpTestData(cls):

        cls.motorcycle = MotorcycleFactory()
        cls.sales_profile = SalesProfileFactory()
        cls.payment = PaymentFactory()

        cls.sales_booking = SalesBookingFactory(
            motorcycle=cls.motorcycle,
            sales_profile=cls.sales_profile,
            payment=cls.payment,
        )

    def test_sales_booking_creation(self):

        self.assertIsInstance(self.sales_booking, SalesBooking)
        self.assertIsNotNone(self.sales_booking.pk)
        self.assertEqual(SalesBooking.objects.count(), 1)

    def test_motorcycle_foreign_key(self):

        field = self.sales_booking._meta.get_field("motorcycle")
        self.assertEqual(field.related_model, self.motorcycle.__class__)

        self.assertEqual(field.remote_field.on_delete, models.PROTECT)
        self.assertEqual(self.sales_booking.motorcycle, self.motorcycle)
        self.assertEqual(
            field.help_text, "The motorcycle associated with this sales booking."
        )

    def test_sales_profile_foreign_key(self):

        field = self.sales_booking._meta.get_field("sales_profile")
        self.assertEqual(field.related_model, self.sales_profile.__class__)

        self.assertEqual(field.remote_field.on_delete, models.PROTECT)
        self.assertEqual(self.sales_booking.sales_profile, self.sales_profile)
        self.assertEqual(
            field.help_text, "The customer's sales profile for this booking."
        )

    def test_payment_one_to_one_field(self):

        field = self.sales_booking._meta.get_field("payment")
        self.assertEqual(field.related_model, self.payment.__class__)

        self.assertEqual(field.remote_field.on_delete, models.SET_NULL)
        self.assertTrue(field.null)
        self.assertTrue(field.blank)
        self.assertEqual(self.sales_booking.payment, self.payment)
        self.assertEqual(
            field.help_text,
            "Link to the associated payment record, if any (e.g., for deposit).",
        )

        self.sales_booking.payment = None
        self.sales_booking.save()
        self.assertIsNone(self.sales_booking.payment)

    def test_sales_booking_reference_field(self):

        field = self.sales_booking._meta.get_field("sales_booking_reference")
        self.assertIsInstance(self.sales_booking.sales_booking_reference, str)
        self.assertEqual(field.max_length, 20)
        self.assertTrue(field.unique)
        self.assertTrue(field.blank)
        self.assertTrue(field.null)
        self.assertEqual(
            field.help_text, "A unique reference code for the sales booking."
        )

        new_booking = SalesBooking(
            motorcycle=self.motorcycle,
            sales_profile=self.sales_profile,
            appointment_date=date.today(),
            appointment_time=time(9, 0),
        )
        new_booking.save()
        self.assertIsNotNone(new_booking.sales_booking_reference)
        self.assertTrue(new_booking.sales_booking_reference.startswith("SBK-"))

        self.assertEqual(len(new_booking.sales_booking_reference), 12)

    def test_amount_paid_field(self):

        new_booking_default_amount = SalesBooking(
            motorcycle=self.motorcycle,
            sales_profile=self.sales_profile,
            appointment_date=date.today(),
            appointment_time=time(10, 0),
        )
        new_booking_default_amount.save()

        field = new_booking_default_amount._meta.get_field("amount_paid")
        self.assertIsInstance(new_booking_default_amount.amount_paid, Decimal)
        self.assertEqual(field.max_digits, 10)
        self.assertEqual(field.decimal_places, 2)

        self.assertEqual(new_booking_default_amount.amount_paid, Decimal("0.00"))
        self.assertEqual(
            field.help_text,
            "The total amount paid for this booking (e.g., deposit or full payment).",
        )

    def test_payment_status_field(self):

        field = self.sales_booking._meta.get_field("payment_status")
        self.assertIsInstance(self.sales_booking.payment_status, str)
        self.assertEqual(field.max_length, 20)
        self.assertEqual(field.choices, PAYMENT_STATUS_CHOICES)
        self.assertEqual(field.default, "unpaid")
        self.assertIn(
            self.sales_booking.payment_status,
            [choice[0] for choice in PAYMENT_STATUS_CHOICES],
        )
        self.assertEqual(
            field.help_text,
            "Current payment status of the booking (e.g., unpaid, deposit_paid, paid).",
        )

    def test_currency_field(self):

        field = self.sales_booking._meta.get_field("currency")
        self.assertIsInstance(self.sales_booking.currency, str)
        self.assertEqual(field.max_length, 3)
        self.assertEqual(field.default, "AUD")
        self.assertEqual(
            field.help_text,
            "The three-letter ISO currency code for the booking (e.g., AUD).",
        )

    def test_stripe_payment_intent_id_field(self):

        field = self.sales_booking._meta.get_field("stripe_payment_intent_id")
        self.assertIsInstance(
            self.sales_booking.stripe_payment_intent_id, (str, type(None))
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
        SalesBookingFactory(
            motorcycle=self.motorcycle,
            sales_profile=self.sales_profile,
            stripe_payment_intent_id=unique_id,
        )
        with self.assertRaises(Exception):
            SalesBookingFactory(
                motorcycle=self.motorcycle,
                sales_profile=self.sales_profile,
                stripe_payment_intent_id=unique_id,
            )

    def test_appointment_date_field(self):

        field = self.sales_booking._meta.get_field("appointment_date")
        self.assertIsInstance(self.sales_booking.appointment_date, date)
        self.assertTrue(field.blank)
        self.assertTrue(field.null)
        self.assertEqual(
            field.help_text,
            "Confirmed date for the test drive, appointment, or pickup.",
        )

    def test_appointment_time_field(self):

        field = self.sales_booking._meta.get_field("appointment_time")
        self.assertIsInstance(self.sales_booking.appointment_time, time)
        self.assertTrue(field.blank)
        self.assertTrue(field.null)
        self.assertEqual(
            field.help_text,
            "Confirmed time for the test drive, appointment, or pickup.",
        )

    def test_booking_status_field(self):

        field = self.sales_booking._meta.get_field("booking_status")
        self.assertIsInstance(self.sales_booking.booking_status, str)
        self.assertEqual(field.max_length, 30)
        self.assertEqual(field.choices, BOOKING_STATUS_CHOICES)
        self.assertEqual(field.default, "pending_confirmation")
        self.assertIn(
            self.sales_booking.booking_status,
            [choice[0] for choice in BOOKING_STATUS_CHOICES],
        )
        self.assertEqual(
            field.help_text,
            "The current status of the sales booking (e.g., confirmed, reserved, enquired, completed).",
        )

    def test_customer_notes_field(self):

        field = self.sales_booking._meta.get_field("customer_notes")
        self.assertIsInstance(self.sales_booking.customer_notes, (str, type(None)))
        self.assertTrue(field.blank)
        self.assertTrue(field.null)
        self.assertEqual(
            field.help_text,
            "Any additional notes or messages provided by the customer.",
        )

    def test_created_at_field(self):

        field = self.sales_booking._meta.get_field("created_at")
        self.assertIsInstance(self.sales_booking.created_at, datetime.datetime)
        self.assertTrue(field.auto_now_add)
        self.assertEqual(
            field.help_text, "The date and time when this sales booking was created."
        )

    def test_updated_at_field(self):

        field = self.sales_booking._meta.get_field("updated_at")
        self.assertIsInstance(self.sales_booking.updated_at, datetime.datetime)
        self.assertTrue(field.auto_now)
        self.assertEqual(
            field.help_text,
            "The date and time when this sales booking was last updated.",
        )

        old_updated_at = self.sales_booking.updated_at
        self.sales_booking.customer_notes = "Updated notes"
        self.sales_booking.save()
        self.assertGreater(self.sales_booking.updated_at, old_updated_at)

    def test_str_method(self):

        expected_str = (
            f"Sales Booking {self.sales_booking.sales_booking_reference} for "
            f"{self.motorcycle.brand} {self.motorcycle.model} "
            f"(Status: {self.sales_booking.get_booking_status_display()})"
        )
        self.assertEqual(str(self.sales_booking), expected_str)

    def test_meta_options(self):

        self.assertEqual(SalesBooking._meta.verbose_name, "Sales Booking")
        self.assertEqual(SalesBooking._meta.verbose_name_plural, "Sales Bookings")
        self.assertEqual(SalesBooking._meta.ordering, ["-created_at"])

    def test_sales_booking_reference_uniqueness(self):

        booking1 = SalesBookingFactory(
            motorcycle=self.motorcycle, sales_profile=self.sales_profile
        )

        with self.assertRaises(Exception):
            SalesBookingFactory(
                motorcycle=self.motorcycle,
                sales_profile=self.sales_profile,
                sales_booking_reference=booking1.sales_booking_reference,
            )
