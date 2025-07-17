from django.test import TestCase
from payments.models import Payment
from payments.tests.test_helpers.model_factories import PaymentFactory
from service.tests.test_helpers.model_factories import (
    ServiceBookingFactory,
    ServiceProfileFactory,
)
from inventory.tests.test_helpers.model_factories import (
    SalesBookingFactory,
    SalesProfileFactory,
)
from django.db import IntegrityError
from decimal import Decimal
import datetime
from django.utils import timezone


class PaymentModelTest(TestCase):
    def test_payment_creation(self):
        payment = PaymentFactory()
        self.assertIsInstance(payment, Payment)
        self.assertIsNotNone(payment.id)
        self.assertIsNotNone(payment.created_at)
        self.assertIsNotNone(payment.updated_at)

    def test_field_properties(self):
        payment = PaymentFactory()

        field = payment._meta.get_field("stripe_payment_intent_id")
        self.assertEqual(field.max_length, 100)
        self.assertTrue(field.unique)
        self.assertTrue(field.null)
        self.assertTrue(field.blank)

        field = payment._meta.get_field("stripe_payment_method_id")
        self.assertEqual(field.max_length, 100)
        self.assertTrue(field.null)
        self.assertTrue(field.blank)

        field = payment._meta.get_field("amount")
        self.assertEqual(field.max_digits, 10)
        self.assertEqual(field.decimal_places, 2)

        field = payment._meta.get_field("currency")
        self.assertEqual(field.max_length, 3)
        self.assertEqual(field.default, "AUD")

        field = payment._meta.get_field("status")
        self.assertEqual(field.max_length, 50)
        self.assertEqual(field.default, "requires_payment_method")

        field = payment._meta.get_field("description")
        self.assertTrue(field.null)
        self.assertTrue(field.blank)

        field = payment._meta.get_field("metadata")
        self.assertEqual(field.default, dict)
        self.assertTrue(field.blank)

        field = payment._meta.get_field("refunded_amount")
        self.assertEqual(field.max_digits, 10)
        self.assertEqual(field.decimal_places, 2)
        self.assertEqual(field.default, Decimal("0.00"))
        self.assertTrue(field.null)
        self.assertTrue(field.blank)

    def test_str_method(self):
        payment = PaymentFactory(
            amount=Decimal("123.45"), currency="USD", status="succeeded"
        )
        expected_str = f"Payment {payment.id} - 123.45 USD - succeeded"
        self.assertEqual(str(payment), expected_str)

    def test_save_method_timestamps(self):
        payment = PaymentFactory()
        old_created_at = payment.created_at
        old_updated_at = payment.updated_at

        import time

        payment.amount = Decimal("99.99")
        time.sleep(0.001)
        payment.save()
        self.assertEqual(payment.created_at, old_created_at)
        self.assertGreater(payment.updated_at, old_updated_at)

    def test_relationships(self):
        service_booking = ServiceBookingFactory()
        sales_booking = SalesBookingFactory()
        service_profile = ServiceProfileFactory()
        sales_profile = SalesProfileFactory()

        payment = PaymentFactory(
            temp_service_booking=None,
            service_booking=service_booking,
            service_customer_profile=service_profile,
            temp_sales_booking=None,
            sales_booking=sales_booking,
            sales_customer_profile=sales_profile,
        )

        self.assertEqual(payment.service_booking, service_booking)
        self.assertEqual(payment.service_customer_profile, service_profile)
        self.assertEqual(payment.sales_booking, sales_booking)
        self.assertEqual(payment.sales_customer_profile, sales_profile)

    def test_stripe_payment_intent_id_unique_constraint(self):
        PaymentFactory(stripe_payment_intent_id="pi_unique_test_id")
        with self.assertRaises(IntegrityError):
            PaymentFactory(stripe_payment_intent_id="pi_unique_test_id")

    def test_json_fields_default_empty_dict(self):
        payment = Payment.objects.create(amount=Decimal("1.00"))
        self.assertEqual(payment.metadata, {})

        payment_with_data = PaymentFactory(metadata={"key": "value"})
        self.assertEqual(payment_with_data.metadata, {"key": "value"})

    def test_refunded_amount_default(self):
        payment = Payment.objects.create(amount=Decimal("1.00"))
        self.assertEqual(payment.refunded_amount, Decimal("0.00"))

    def test_ordering(self):
        now = timezone.now()

        payment1 = PaymentFactory()
        payment1.created_at = now - datetime.timedelta(days=3)
        payment1.save()

        payment2 = PaymentFactory()
        payment2.created_at = now - datetime.timedelta(days=1)
        payment2.save()

        payment3 = PaymentFactory()
        payment3.created_at = now - datetime.timedelta(days=2)
        payment3.save()

        ordered_payments = list(Payment.objects.order_by("-created_at"))
        self.assertEqual(ordered_payments[0].id, payment2.id)
        self.assertEqual(ordered_payments[1].id, payment3.id)
        self.assertEqual(ordered_payments[2].id, payment1.id)
