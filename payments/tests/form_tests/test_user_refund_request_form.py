from django.test import TestCase
from decimal import Decimal

from payments.forms.user_refund_request_form import RefundRequestForm
from payments.models import RefundRequest
from payments.tests.test_helpers.model_factories import (
    PaymentFactory,
    SalesBookingFactory,
    SalesProfileFactory,
    ServiceBookingFactory,
    ServiceProfileFactory,
    RefundRequestFactory,
    UserFactory,
)


class UserRefundRequestFormTests(TestCase):

    def setUp(self):

        self.user = UserFactory()
        self.service_profile = ServiceProfileFactory(
            email="service.customer@example.com", user=self.user
        )
        self.sales_profile = SalesProfileFactory(
            email="sales.customer@example.com", user=self.user
        )

        payment_service = PaymentFactory(
            status="succeeded",
            service_customer_profile=self.service_profile,
            amount=Decimal("150.00"),
        )
        self.service_booking = ServiceBookingFactory(
            payment=payment_service, service_profile=self.service_profile
        )
        payment_service.service_booking = self.service_booking
        payment_service.save()

        payment_sales = PaymentFactory(
            status="succeeded",
            sales_customer_profile=self.sales_profile,
            amount=Decimal("500.00"),
        )
        self.sales_booking = SalesBookingFactory(
            payment=payment_sales, sales_profile=self.sales_profile
        )
        payment_sales.sales_booking = self.sales_booking
        payment_sales.save()

    def test_valid_service_booking_request(self):

        form_data = {
            "booking_reference": self.service_booking.service_booking_reference,
            "email": self.service_profile.email,
            "reason": "Service was not as expected.",
        }
        form = RefundRequestForm(data=form_data)
        self.assertTrue(
            form.is_valid(),
            f"Form should be valid but has errors: {form.errors.as_json()}",
        )

        instance = form.save()
        self.assertIsNotNone(instance.pk)
        self.assertEqual(instance.payment, self.service_booking.payment)
        self.assertEqual(instance.service_booking, self.service_booking)
        self.assertEqual(instance.service_profile, self.service_profile)
        self.assertEqual(instance.status, "unverified")
        self.assertFalse(instance.is_admin_initiated)
        self.assertIsNone(instance.sales_booking)

    def test_valid_sales_booking_request(self):

        form_data = {
            "booking_reference": self.sales_booking.sales_booking_reference,
            "email": self.sales_profile.email,
            "reason": "Changed my mind about the purchase.",
        }
        form = RefundRequestForm(data=form_data)
        self.assertTrue(
            form.is_valid(),
            f"Form should be valid but has errors: {form.errors.as_json()}",
        )

        instance = form.save()
        self.assertIsNotNone(instance.pk)
        self.assertEqual(instance.payment, self.sales_booking.payment)
        self.assertEqual(instance.sales_booking, self.sales_booking)
        self.assertEqual(instance.sales_profile, self.sales_profile)
        self.assertEqual(instance.status, "unverified")
        self.assertFalse(instance.is_admin_initiated)

        self.assertIsNone(instance.service_booking)
