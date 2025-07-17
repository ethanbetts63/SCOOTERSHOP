from decimal import Decimal
from django.test import TestCase, override_settings
from unittest import mock
from django.conf import settings


from inventory.models import SalesBooking, TempSalesBooking
from payments.webhook_handlers.sales_handlers import handle_sales_booking_succeeded


from users.tests.test_helpers.model_factories import UserFactory
from inventory.tests.test_helpers.model_factories import (
    SalesProfileFactory,
    MotorcycleFactory,
    TempSalesBookingFactory,
    SalesBookingFactory,
    MotorcycleConditionFactory,
)
from payments.tests.test_helpers.model_factories import PaymentFactory


@override_settings(ADMIN_EMAIL="admin-sales@example.com")
class SalesWebhookHandlerTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(email="salesuser@example.com")
        cls.sales_profile = SalesProfileFactory(user=cls.user)

        cls.condition_new = MotorcycleConditionFactory(name="new", display_name="New")
        cls.condition_used = MotorcycleConditionFactory(
            name="used", display_name="Used"
        )

        cls.motorcycle = MotorcycleFactory(
            price=Decimal("10000.00"),
            status="for_sale",
            is_available=True,
            conditions=[cls.condition_used],
        )

    def test_handle_sales_booking_succeeded_deposit_flow(self):
        deposit_amount = Decimal("500.00")
        temp_booking = TempSalesBookingFactory(
            motorcycle=self.motorcycle,
            sales_profile=self.sales_profile,
            amount_paid=deposit_amount,
            deposit_required_for_flow=True,
            booking_status="pending_details",
        )
        payment_obj = PaymentFactory(
            temp_sales_booking=temp_booking,
            amount=deposit_amount,
            status="requires_payment_method",
            stripe_payment_intent_id=temp_booking.stripe_payment_intent_id,
        )
        payment_intent_data = {
            "id": payment_obj.stripe_payment_intent_id,
            "amount_received": int(deposit_amount * 100),
            "status": "succeeded",
            "currency": "AUD",
        }

        with mock.patch(
            "payments.webhook_handlers.sales_handlers.send_templated_email"
        ) as mock_send_email:
            handle_sales_booking_succeeded(payment_obj, payment_intent_data)

            with self.assertRaises(TempSalesBooking.DoesNotExist):
                TempSalesBooking.objects.get(id=temp_booking.id)

            sales_booking = SalesBooking.objects.get(
                stripe_payment_intent_id=payment_obj.stripe_payment_intent_id
            )
            self.assertIsNotNone(sales_booking)
            self.assertEqual(sales_booking.payment_status, "deposit_paid")
            self.assertEqual(sales_booking.booking_status, "pending_confirmation")
            self.assertEqual(sales_booking.amount_paid, deposit_amount)

            motorcycle_after_booking = sales_booking.motorcycle
            motorcycle_after_booking.refresh_from_db()
            self.assertEqual(motorcycle_after_booking.status, "reserved")
            self.assertFalse(motorcycle_after_booking.is_available)
            self.assertEqual(motorcycle_after_booking.quantity, 1)

            payment_obj.refresh_from_db()
            self.assertEqual(payment_obj.status, "succeeded")
            self.assertEqual(payment_obj.sales_booking, sales_booking)

            self.assertEqual(mock_send_email.call_count, 2)

            mock_send_email.assert_any_call(
                recipient_list=[self.user.email],
                subject=f"Your Sales Booking Confirmation - {sales_booking.sales_booking_reference}",
                template_name="user_sales_booking_confirmation.html",
                context=mock.ANY,
                booking=sales_booking,
                profile=self.sales_profile,
            )

            mock_send_email.assert_any_call(
                recipient_list=[settings.ADMIN_EMAIL],
                subject=f"New Sales Booking (Online) - {sales_booking.sales_booking_reference}",
                template_name="admin_sales_booking_confirmation.html",
                context=mock.ANY,
                booking=sales_booking,
                profile=self.sales_profile,
            )

    def test_handle_sales_booking_succeeded_temp_booking_missing(self):
        payment_obj = PaymentFactory(temp_sales_booking=None)
        payment_intent_data = {
            "status": "succeeded",
            "amount_received": 50000,
            "currency": "AUD",
        }

        with self.assertRaises(TempSalesBooking.DoesNotExist):
            handle_sales_booking_succeeded(payment_obj, payment_intent_data)

    def test_handle_sales_booking_succeeded_rollback_on_error(self):
        temp_booking = TempSalesBookingFactory(
            motorcycle=self.motorcycle,
            sales_profile=self.sales_profile,
            deposit_required_for_flow=True,
        )
        payment_obj = PaymentFactory(temp_sales_booking=temp_booking)
        payment_intent_data = {
            "status": "succeeded",
            "amount_received": 50000,
            "currency": "AUD",
        }

        initial_motorcycle_status = self.motorcycle.status
        initial_motorcycle_availability = self.motorcycle.is_available

        with mock.patch(
            "payments.webhook_handlers.sales_handlers.convert_temp_sales_booking",
            side_effect=ValueError("Simulated DB error"),
        ):
            with self.assertRaises(ValueError):
                handle_sales_booking_succeeded(payment_obj, payment_intent_data)

            self.assertTrue(
                TempSalesBooking.objects.filter(id=temp_booking.id).exists()
            )
            self.assertFalse(SalesBooking.objects.exists())
            payment_obj.refresh_from_db()
            self.assertIsNone(payment_obj.sales_booking)

            self.motorcycle.refresh_from_db()
            self.assertEqual(self.motorcycle.status, initial_motorcycle_status)
            self.assertEqual(
                self.motorcycle.is_available, initial_motorcycle_availability
            )

    def test_handle_sales_booking_already_converted(self):
        sales_booking = SalesBookingFactory(
            motorcycle=self.motorcycle, sales_profile=self.sales_profile
        )
        payment_obj = PaymentFactory(
            sales_booking=sales_booking,
            status="requires_payment_method",
            stripe_payment_intent_id=sales_booking.stripe_payment_intent_id,
        )
        payment_intent_data = {
            "id": payment_obj.stripe_payment_intent_id,
            "amount_received": int(sales_booking.amount_paid * 100),
            "status": "succeeded",
            "currency": "AUD",
        }

        with mock.patch(
            "payments.webhook_handlers.sales_handlers.convert_temp_sales_booking"
        ) as mock_convert:
            with mock.patch(
                "payments.webhook_handlers.sales_handlers.send_templated_email"
            ) as mock_send_email:
                handle_sales_booking_succeeded(payment_obj, payment_intent_data)

                self.assertFalse(mock_convert.called)
                payment_obj.refresh_from_db()
                self.assertEqual(payment_obj.status, "succeeded")
                self.assertEqual(mock_send_email.call_count, 0)

    def test_handle_sales_booking_succeeded_new_bike_decrements_quantity(self):

        new_motorcycle = MotorcycleFactory(
            price=Decimal("15000.00"),
            status="for_sale",
            is_available=True,
            quantity=5,
            conditions=[self.condition_new],
        )
        initial_quantity = new_motorcycle.quantity

        deposit_amount = Decimal("500.00")
        temp_booking = TempSalesBookingFactory(
            motorcycle=new_motorcycle,
            sales_profile=self.sales_profile,
            amount_paid=deposit_amount,
            deposit_required_for_flow=True,
            booking_status="pending_details",
        )
        payment_obj = PaymentFactory(
            temp_sales_booking=temp_booking,
            amount=deposit_amount,
            status="requires_payment_method",
            stripe_payment_intent_id=temp_booking.stripe_payment_intent_id,
        )
        payment_intent_data = {
            "id": payment_obj.stripe_payment_intent_id,
            "amount_received": int(deposit_amount * 100),
            "status": "succeeded",
            "currency": "AUD",
        }

        with mock.patch(
            "payments.webhook_handlers.sales_handlers.send_templated_email"
        ):
            handle_sales_booking_succeeded(payment_obj, payment_intent_data)

            new_motorcycle.refresh_from_db()
            self.assertEqual(new_motorcycle.quantity, initial_quantity - 1)
            self.assertTrue(new_motorcycle.is_available)
            self.assertEqual(new_motorcycle.status, "for_sale")

            sales_booking = SalesBooking.objects.get(
                stripe_payment_intent_id=payment_obj.stripe_payment_intent_id
            )
            self.assertEqual(sales_booking.payment_status, "deposit_paid")

    def test_handle_sales_booking_succeeded_new_bike_quantity_to_zero(self):

        new_motorcycle = MotorcycleFactory(
            price=Decimal("12000.00"),
            status="for_sale",
            is_available=True,
            quantity=1,
            conditions=[self.condition_new],
        )
        initial_quantity = new_motorcycle.quantity

        deposit_amount = Decimal("500.00")
        temp_booking = TempSalesBookingFactory(
            motorcycle=new_motorcycle,
            sales_profile=self.sales_profile,
            amount_paid=deposit_amount,
            deposit_required_for_flow=True,
            booking_status="pending_details",
        )
        payment_obj = PaymentFactory(
            temp_sales_booking=temp_booking,
            amount=deposit_amount,
            status="requires_payment_method",
            stripe_payment_intent_id=temp_booking.stripe_payment_intent_id,
        )
        payment_intent_data = {
            "id": payment_obj.stripe_payment_intent_id,
            "amount_received": int(deposit_amount * 100),
            "status": "succeeded",
            "currency": "AUD",
        }

        with mock.patch(
            "payments.webhook_handlers.sales_handlers.send_templated_email"
        ):
            handle_sales_booking_succeeded(payment_obj, payment_intent_data)

            new_motorcycle.refresh_from_db()
            self.assertEqual(new_motorcycle.quantity, 0)
            self.assertFalse(new_motorcycle.is_available)
            self.assertEqual(new_motorcycle.status, "sold")

            sales_booking = SalesBooking.objects.get(
                stripe_payment_intent_id=payment_obj.stripe_payment_intent_id
            )
            self.assertEqual(sales_booking.payment_status, "deposit_paid")
