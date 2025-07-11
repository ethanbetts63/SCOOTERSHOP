from django.test import TestCase
from decimal import Decimal
from refunds.forms.admin_refund_request_form import AdminRefundRequestForm
from refunds.models.RefundRequest import RefundRequest

from payments.tests.test_helpers.model_factories import (
    PaymentFactory,
    UserFactory,
    SalesBookingFactory,
    SalesProfileFactory,
    MotorcycleFactory,
    ServiceBookingFactory,
    ServiceProfileFactory,
    CustomerMotorcycleFactory,
    ServiceTypeFactory,
)


class AdminRefundRequestFormTests(TestCase):

    def setUp(self):

        self.admin_user = UserFactory(
            username="admin", email="admin@example.com", is_staff=True
        )
        self.sales_profile = SalesProfileFactory(user=self.admin_user)
        self.service_profile = ServiceProfileFactory(user=self.admin_user)
        self.motorcycle_gen = MotorcycleFactory()

        self.motorcycle_service = CustomerMotorcycleFactory(
            service_profile=self.service_profile
        )
        self.service_type_obj = ServiceTypeFactory()
        self.payment_succeeded_service = PaymentFactory(
            amount=Decimal("250.00"),
            status="succeeded",
            service_customer_profile=self.service_profile,
            stripe_payment_intent_id="pi_test_succeeded_service",
        )
        self.service_booking_paid = ServiceBookingFactory(
            service_profile=self.service_profile,
            customer_motorcycle=self.motorcycle_service,
            service_type=self.service_type_obj,
            payment=self.payment_succeeded_service,
            amount_paid=self.payment_succeeded_service.amount,
            calculated_total=self.payment_succeeded_service.amount,
            payment_status="paid",
            booking_status="confirmed",
        )
        self.payment_succeeded_service.service_booking = self.service_booking_paid
        self.payment_succeeded_service.save()

        self.motorcycle_sales = MotorcycleFactory()
        self.payment_deposit_sales = PaymentFactory(
            amount=Decimal("100.00"),
            status="succeeded",
            sales_customer_profile=self.sales_profile,
            stripe_payment_intent_id="pi_test_deposit_sales",
        )
        self.sales_booking_deposit = SalesBookingFactory(
            sales_profile=self.sales_profile,
            motorcycle=self.motorcycle_sales,
            payment=self.payment_deposit_sales,
            amount_paid=self.payment_deposit_sales.amount,
            payment_status="deposit_paid",
            booking_status="deposit_paid",
        )
        self.payment_deposit_sales.sales_booking = self.sales_booking_deposit
        self.payment_deposit_sales.save()

    def test_form_valid_data_create_service(self):

        form_data = {
            "service_booking": self.service_booking_paid.pk,
            "reason": "Customer requested service refund.",
            "staff_notes": "Service refund processed.",
            "amount_to_refund": "250.00",
        }
        form = AdminRefundRequestForm(data=form_data)
        self.assertTrue(form.is_valid(), f"Form is not valid: {form.errors}")

        refund_request = form.save()
        self.assertIsInstance(refund_request, RefundRequest)
        self.assertEqual(refund_request.service_booking, self.service_booking_paid)
        self.assertEqual(refund_request.payment, self.payment_succeeded_service)
        self.assertEqual(refund_request.service_profile, self.service_profile)
        self.assertEqual(refund_request.reason, "Customer requested service refund.")
        self.assertEqual(refund_request.staff_notes, "Service refund processed.")
        self.assertEqual(refund_request.amount_to_refund, Decimal("250.00"))
        self.assertIsNotNone(refund_request.requested_at)
        self.assertEqual(RefundRequest.objects.count(), 1)

    def test_form_valid_data_create_sales(self):

        form_data = {
            "sales_booking": self.sales_booking_deposit.pk,
            "reason": "Customer cancelled sale.",
            "staff_notes": "Sales deposit refund initiated.",
            "amount_to_refund": "100.00",
        }
        form = AdminRefundRequestForm(data=form_data)
        self.assertTrue(form.is_valid(), f"Form is not valid: {form.errors}")

        refund_request = form.save()
        self.assertIsInstance(refund_request, RefundRequest)
        self.assertEqual(refund_request.sales_booking, self.sales_booking_deposit)
        self.assertEqual(refund_request.payment, self.payment_deposit_sales)
        self.assertEqual(refund_request.sales_profile, self.sales_profile)
        self.assertEqual(refund_request.reason, "Customer cancelled sale.")
        self.assertEqual(refund_request.staff_notes, "Sales deposit refund initiated.")
        self.assertEqual(refund_request.amount_to_refund, Decimal("100.00"))
        self.assertIsNotNone(refund_request.requested_at)
        self.assertEqual(RefundRequest.objects.count(), 1)

    def test_form_invalid_no_booking_selected(self):

        form_data = {
            "reason": "Test reason",
            "staff_notes": "Test notes",
            "amount_to_refund": "100.00",
        }
        form = AdminRefundRequestForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("__all__", form.errors)
        self.assertEqual(
            form.errors["__all__"], ["Please select a Service, or Sales Booking."]
        )

    def test_form_invalid_multiple_bookings_selected(self):

        form_data = {
            "service_booking": self.service_booking_paid.pk,
            "sales_booking": self.sales_booking_deposit.pk,
            "reason": "Test reason",
            "staff_notes": "Test notes",
            "amount_to_refund": "100.00",
        }
        form = AdminRefundRequestForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("__all__", form.errors)
        self.assertEqual(
            form.errors["__all__"],
            ["Please select only one type of booking (Service, or Sales)."],
        )

    def test_form_initial_values_for_new_instance(self):

        form = AdminRefundRequestForm()
        self.assertIsNone(form.initial.get("is_admin_initiated"))
        self.assertIsNone(form.initial.get("status"))

    def test_form_edit_instance_service_booking(self):

        existing_refund_request = RefundRequest.objects.create(
            service_booking=self.service_booking_paid,
            payment=self.payment_succeeded_service,
            service_profile=self.service_profile,
            reason="Original service reason",
            staff_notes="Original service notes",
            amount_to_refund=Decimal("150.00"),
            is_admin_initiated=True,
            status="pending",
        )

        form_data = {
            "service_booking": self.service_booking_paid.pk,
            "reason": "Updated service reason",
            "staff_notes": "Updated service notes.",
            "amount_to_refund": "200.00",
        }
        form = AdminRefundRequestForm(data=form_data, instance=existing_refund_request)
        self.assertTrue(form.is_valid(), f"Form is not valid: {form.errors}")

        updated_refund_request = form.save()
        self.assertEqual(updated_refund_request.pk, existing_refund_request.pk)
        self.assertEqual(updated_refund_request.reason, "Updated service reason")
        self.assertEqual(updated_refund_request.staff_notes, "Updated service notes.")
        self.assertEqual(updated_refund_request.amount_to_refund, Decimal("200.00"))
        self.assertEqual(updated_refund_request.status, "pending")
        self.assertTrue(updated_refund_request.is_admin_initiated)
        self.assertEqual(RefundRequest.objects.count(), 1)

    def test_form_edit_instance_sales_booking(self):

        existing_refund_request = RefundRequest.objects.create(
            sales_booking=self.sales_booking_deposit,
            payment=self.payment_deposit_sales,
            sales_profile=self.sales_profile,
            reason="Original sales reason",
            staff_notes="Original sales notes",
            amount_to_refund=Decimal("50.00"),
            is_admin_initiated=True,
            status="pending",
        )

        form_data = {
            "sales_booking": self.sales_booking_deposit.pk,
            "reason": "Updated sales reason",
            "staff_notes": "Updated sales notes.",
            "amount_to_refund": "75.00",
        }
        form = AdminRefundRequestForm(data=form_data, instance=existing_refund_request)
        self.assertTrue(form.is_valid(), f"Form is not valid: {form.errors}")

        updated_refund_request = form.save()
        self.assertEqual(updated_refund_request.pk, existing_refund_request.pk)
        self.assertEqual(updated_refund_request.reason, "Updated sales reason")
        self.assertEqual(updated_refund_request.staff_notes, "Updated sales notes.")
        self.assertEqual(updated_refund_request.amount_to_refund, Decimal("75.00"))
        self.assertEqual(updated_refund_request.status, "pending")
        self.assertTrue(updated_refund_request.is_admin_initiated)
        self.assertEqual(RefundRequest.objects.count(), 1)
