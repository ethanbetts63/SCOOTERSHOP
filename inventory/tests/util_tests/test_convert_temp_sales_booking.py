from django.test import TestCase
from decimal import Decimal
import datetime
from unittest import mock

from inventory.models import (
    TempSalesBooking,
    SalesBooking,
    InventorySettings,
)
from inventory.utils.convert_temp_sales_booking import convert_temp_sales_booking
from inventory.tests.test_helpers.model_factories import (
    TempSalesBookingFactory,
    SalesProfileFactory,
    MotorcycleFactory,
    InventorySettingsFactory,
)
from payments.tests.test_helpers.model_factories import PaymentFactory
from refunds.tests.test_helpers.model_factories import RefundSettingsFactory


class ConvertTempSalesBookingUtilTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.inventory_settings = InventorySettingsFactory(
            currency_code="USD",
        )

        cls.refund_settings = RefundSettingsFactory()

        cls.motorcycle = MotorcycleFactory(status="available", is_available=True)
        cls.sales_profile = SalesProfileFactory()

    def setUp(self):
        self.motorcycle.refresh_from_db()
        self.motorcycle.status = "for_sale"
        self.motorcycle.is_available = True
        self.motorcycle.save()

    def test_basic_conversion_unpaid(self):
        temp_booking = TempSalesBookingFactory(
            motorcycle=self.motorcycle,
            sales_profile=self.sales_profile,
            amount_paid=Decimal("0.00"),
            payment_status="unpaid",
            appointment_date=datetime.date(2025, 7, 1),
            appointment_time=datetime.time(10, 0),
            customer_notes="Initial enquiry",
        )

        initial_temp_booking_count = TempSalesBooking.objects.count()
        initial_sales_booking_count = SalesBooking.objects.count()

        sales_booking = convert_temp_sales_booking(
            temp_booking=temp_booking,
            booking_payment_status="unpaid",
            amount_paid_on_booking=Decimal("0.00"),
        )

        self.assertIsNotNone(sales_booking)
        self.assertIsInstance(sales_booking, SalesBooking)
        self.assertEqual(SalesBooking.objects.count(), initial_sales_booking_count + 1)
        self.assertEqual(sales_booking.motorcycle, self.motorcycle)
        self.assertEqual(sales_booking.sales_profile, self.sales_profile)
        self.assertEqual(sales_booking.amount_paid, Decimal("0.00"))
        self.assertEqual(sales_booking.payment_status, "unpaid")
        self.assertEqual(sales_booking.currency, self.inventory_settings.currency_code)
        self.assertEqual(sales_booking.booking_status, "pending_confirmation")
        self.assertEqual(sales_booking.appointment_date, datetime.date(2025, 7, 1))
        self.assertEqual(sales_booking.appointment_time, datetime.time(10, 0))
        self.assertEqual(sales_booking.customer_notes, "Initial enquiry")

        self.assertEqual(
            TempSalesBooking.objects.count(), initial_temp_booking_count - 1
        )
        self.assertFalse(TempSalesBooking.objects.filter(pk=temp_booking.pk).exists())

        self.motorcycle.refresh_from_db()
        self.assertEqual(self.motorcycle.status, "for_sale")
        self.assertTrue(self.motorcycle.is_available)

    def test_conversion_with_payment_object(self):
        payment_obj = PaymentFactory(
            temp_sales_booking=None,
            amount=Decimal("0.00"),
            currency="AUD",
            status="unpaid",
        )
        temp_booking = TempSalesBookingFactory(
            motorcycle=self.motorcycle,
            sales_profile=self.sales_profile,
            amount_paid=Decimal("0.00"),
            payment_status="unpaid",
            payment=payment_obj,
        )

        amount_to_pay = Decimal("250.00")
        new_payment_status = "deposit_paid"
        stripe_id = "pi_xyz789"

        sales_booking = convert_temp_sales_booking(
            temp_booking=temp_booking,
            booking_payment_status=new_payment_status,
            amount_paid_on_booking=amount_to_pay,
            stripe_payment_intent_id=stripe_id,
            payment_obj=payment_obj,
        )

        self.assertIsNotNone(sales_booking)
        self.assertEqual(sales_booking.payment, payment_obj)

        payment_obj.refresh_from_db()
        self.assertEqual(payment_obj.amount, amount_to_pay)
        self.assertEqual(payment_obj.currency, self.inventory_settings.currency_code)
        self.assertEqual(payment_obj.status, new_payment_status)
        self.assertEqual(payment_obj.stripe_payment_intent_id, stripe_id)
        self.assertEqual(payment_obj.sales_booking, sales_booking)
        self.assertEqual(
            payment_obj.sales_customer_profile, sales_booking.sales_profile
        )
        self.assertIsNone(payment_obj.temp_sales_booking)

        self.assertFalse(TempSalesBooking.objects.filter(pk=temp_booking.pk).exists())

    def test_conversion_no_inventory_settings(self):
        InventorySettingsFactory()._meta.model.objects.all().delete()
        self.assertFalse(InventorySettings.objects.exists())

        temp_booking = TempSalesBookingFactory(
            motorcycle=self.motorcycle,
            sales_profile=self.sales_profile,
        )

        sales_booking = convert_temp_sales_booking(
            temp_booking=temp_booking,
            booking_payment_status="unpaid",
            amount_paid_on_booking=Decimal("0.00"),
        )

        self.assertEqual(sales_booking.currency, "AUD")

        self.inventory_settings = InventorySettingsFactory(pk=1)

    def test_conversion_handles_exception(self):
        temp_booking = TempSalesBookingFactory(
            motorcycle=self.motorcycle,
            sales_profile=self.sales_profile,
        )

        with mock.patch("inventory.models.SalesBooking.objects.create") as mock_create:
            mock_create.side_effect = Exception("Database error simulation")

            with self.assertRaisesMessage(Exception, "Database error simulation"):
                convert_temp_sales_booking(
                    temp_booking=temp_booking,
                    booking_payment_status="unpaid",
                    amount_paid_on_booking=Decimal("0.00"),
                )

            self.assertEqual(SalesBooking.objects.count(), 0)

            self.assertTrue(
                TempSalesBooking.objects.filter(pk=temp_booking.pk).exists()
            )
