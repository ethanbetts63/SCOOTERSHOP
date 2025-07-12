from django.test import TestCase
from decimal import Decimal
from unittest.mock import patch


from service.models import TempServiceBooking, ServiceBooking, ServiceSettings
from payments.models import Payment, RefundSettings

from service.utils.convert_temp_service_booking import convert_temp_service_booking


from ..test_helpers.model_factories import (
    TempServiceBookingFactory,
    ServiceSettingsFactory,
    RefundSettingsFactory,
    PaymentFactory,
    ServiceTypeFactory,
    ServiceProfileFactory,
    CustomerMotorcycleFactory,
)


class ConvertTempServiceBookingTest(TestCase):

    @classmethod
    def setUpTestData(cls):

        cls.service_settings = ServiceSettingsFactory(currency_code="AUD")
        cls.service_type = ServiceTypeFactory()
        cls.service_profile = ServiceProfileFactory()
        cls.customer_motorcycle = CustomerMotorcycleFactory(
            service_profile=cls.service_profile
        )

        cls.refund_policy_settings = RefundSettingsFactory()

    def setUp(self):

        TempServiceBooking.objects.all().delete()
        ServiceBooking.objects.all().delete()
        Payment.objects.all().delete()

        ServiceSettings.objects.all().delete()
        RefundSettings.objects.all().delete()
        self.service_settings = ServiceSettingsFactory(currency_code="AUD")
        self.refund_policy_settings = RefundSettingsFactory()

    def test_successful_conversion_without_payment_object(self):

        temp_booking = TempServiceBookingFactory(
            service_type=self.service_type,
            service_profile=self.service_profile,
            customer_motorcycle=self.customer_motorcycle,
            payment_method="in_store_full",
            calculated_total=Decimal("150.00"),
            calculated_deposit_amount=Decimal("0.00"),
        )

        amount_paid = Decimal("0.00")
        calculated_total = Decimal("150.00")

        service_booking = convert_temp_service_booking(
            temp_booking=temp_booking,
            payment_method="in_store_full",
            booking_payment_status="unpaid",
            amount_paid_on_booking=amount_paid,
            calculated_total_on_booking=calculated_total,
            stripe_payment_intent_id=None,
        )

        self.assertIsInstance(service_booking, ServiceBooking)
        self.assertFalse(TempServiceBooking.objects.filter(pk=temp_booking.pk).exists())
        self.assertEqual(ServiceBooking.objects.count(), 1)
        self.assertEqual(Payment.objects.count(), 0)

        self.assertIsNone(service_booking.payment)

        self.assertEqual(service_booking.amount_paid, amount_paid)
        self.assertEqual(service_booking.payment_status, "unpaid")
        self.assertEqual(service_booking.payment_method, "in_store_full")

    def test_successful_conversion_with_existing_payment_object(self):

        existing_payment = PaymentFactory(
            amount=Decimal("50.00"),
            currency="USD",
            status="requires_payment_method",
            temp_service_booking=None,
            service_booking=None,
        )

        temp_booking = TempServiceBookingFactory(
            service_type=self.service_type,
            service_profile=self.service_profile,
            customer_motorcycle=self.customer_motorcycle,
            payment_method="online_full",
            calculated_total=Decimal("200.00"),
            calculated_deposit_amount=Decimal("0.00"),
        )

        amount_paid = Decimal("200.00")
        calculated_total = Decimal("200.00")

        service_booking = convert_temp_service_booking(
            temp_booking=temp_booking,
            payment_method="online_full",
            booking_payment_status="paid",
            amount_paid_on_booking=amount_paid,
            calculated_total_on_booking=calculated_total,
            stripe_payment_intent_id="pi_test_456",
            payment_obj=existing_payment,
        )

        self.assertIsInstance(service_booking, ServiceBooking)
        self.assertFalse(TempServiceBooking.objects.filter(pk=temp_booking.pk).exists())
        self.assertEqual(ServiceBooking.objects.count(), 1)
        self.assertEqual(Payment.objects.count(), 1)

        updated_payment = Payment.objects.get(pk=existing_payment.pk)
        self.assertEqual(updated_payment.amount, amount_paid)
        self.assertEqual(updated_payment.currency, "AUD")
        self.assertEqual(updated_payment.stripe_payment_intent_id, "pi_test_456")
        self.assertEqual(updated_payment.service_booking, service_booking)
        self.assertEqual(updated_payment.service_customer_profile, self.service_profile)
        self.assertIsNone(updated_payment.temp_service_booking)

        self.assertIsNotNone(updated_payment.refund_policy_snapshot)
        self.assertIsInstance(updated_payment.refund_policy_snapshot, dict)
        self.assertGreater(len(updated_payment.refund_policy_snapshot), 0)
        self.assertIn(
            "full_payment_full_refund_days",
            updated_payment.refund_policy_snapshot,
        )

    def test_conversion_without_refund_policy_settings(self):

        RefundSettings.objects.all().delete()
        self.assertEqual(RefundSettings.objects.count(), 0)

        temp_booking = TempServiceBookingFactory(
            service_type=self.service_type,
            service_profile=self.service_profile,
            customer_motorcycle=self.customer_motorcycle,
            payment_method="online_full",
            calculated_total=Decimal("100.00"),
            calculated_deposit_amount=Decimal("0.00"),
        )

        payment_obj = PaymentFactory(
            amount=Decimal("0.00"),
            currency="AUD",
            status="requires_payment_method",
            temp_service_booking=None,
            service_booking=None,
        )

        convert_temp_service_booking(
            temp_booking=temp_booking,
            payment_method="online_full",
            booking_payment_status="paid",
            amount_paid_on_booking=Decimal("100.00"),
            calculated_total_on_booking=Decimal("100.00"),
            payment_obj=payment_obj,
        )

        updated_payment = Payment.objects.get(pk=payment_obj.pk)
        self.assertEqual(updated_payment.refund_policy_snapshot, {})

    @patch(
        "service.models.ServiceBooking.objects.create",
        side_effect=Exception("Database error!"),
    )
    def test_exception_during_service_booking_creation(self, mock_create):

        temp_booking = TempServiceBookingFactory(
            service_type=self.service_type,
            service_profile=self.service_profile,
            customer_motorcycle=self.customer_motorcycle,
            payment_method="online_full",
            calculated_total=Decimal("100.00"),
            calculated_deposit_amount=Decimal("0.00"),
        )

        with self.assertRaisesMessage(Exception, "Database error!"):
            convert_temp_service_booking(
                temp_booking=temp_booking,
                payment_method="online_full",
                booking_payment_status="paid",
                amount_paid_on_booking=Decimal("100.00"),
                calculated_total_on_booking=Decimal("100.00"),
                payment_obj=None,
            )

        self.assertEqual(ServiceBooking.objects.count(), 0)

        self.assertEqual(Payment.objects.count(), 0)

        self.assertTrue(TempServiceBooking.objects.filter(pk=temp_booking.pk).exists())

    def test_temp_service_booking_deleted_on_successful_conversion(self):

        temp_booking = TempServiceBookingFactory(
            service_type=self.service_type,
            service_profile=self.service_profile,
            customer_motorcycle=self.customer_motorcycle,
            payment_method="in_store_full",
            calculated_total=Decimal("100.00"),
            calculated_deposit_amount=Decimal("0.00"),
        )
        temp_booking_pk = temp_booking.pk

        convert_temp_service_booking(
            temp_booking=temp_booking,
            payment_method="in_store_full",
            booking_payment_status="unpaid",
            amount_paid_on_booking=Decimal("0.00"),
            calculated_total_on_booking=Decimal("100.00"),
            payment_obj=None,
        )

        self.assertFalse(TempServiceBooking.objects.filter(pk=temp_booking_pk).exists())
        self.assertEqual(Payment.objects.count(), 0)
        self.assertEqual(ServiceBooking.objects.count(), 1)

    @patch("service.utils.convert_temp_service_booking.send_booking_to_mechanicdesk")
    def test_conversion_calls_mechanicdesk_sender(self, mock_mechanicdesk_sender):

        temp_booking = TempServiceBookingFactory(
            service_type=self.service_type,
            service_profile=self.service_profile,
            customer_motorcycle=self.customer_motorcycle,
            payment_method="online_full",
            calculated_total=Decimal("250.00"),
            calculated_deposit_amount=Decimal("50.00"),
        )

        payment_obj = PaymentFactory(
            amount=Decimal("50.00"),
            currency="AUD",
            status="deposit_paid",
            temp_service_booking=temp_booking,
        )

        service_booking = convert_temp_service_booking(
            temp_booking=temp_booking,
            payment_method="online_deposit",
            booking_payment_status="deposit_paid",
            amount_paid_on_booking=Decimal("50.00"),
            calculated_total_on_booking=Decimal("250.00"),
            stripe_payment_intent_id="pi_test_mechanicdesk_call",
            payment_obj=payment_obj,
        )

        self.assertIsInstance(service_booking, ServiceBooking)
        self.assertEqual(ServiceBooking.objects.count(), 1)

        self.assertFalse(TempServiceBooking.objects.filter(pk=temp_booking.pk).exists())

        mock_mechanicdesk_sender.assert_called_once_with(service_booking)
