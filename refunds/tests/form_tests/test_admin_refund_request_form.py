from django.test import TestCase
from decimal import Decimal
from django.apps import apps
from refunds.forms.admin_refund_request_form import AdminRefundRequestForm
from refunds.tests.test_helpers.model_factories import RefundRequestFactory

from payments.tests.test_helpers.model_factories import PaymentFactory
from users.tests.test_helpers.model_factories import UserFactory, StaffUserFactory
from inventory.tests.test_helpers.model_factories import (
    SalesBookingFactory,
    SalesProfileFactory,
    MotorcycleFactory,
)
from service.tests.test_helpers.model_factories import (
    ServiceBookingFactory,
    ServiceProfileFactory,
    CustomerMotorcycleFactory,
    ServiceTypeFactory,
)

RefundRequest = apps.get_model('refunds', 'RefundRequest')


class AdminRefundRequestFormTests(TestCase):
    def setUp(self):
        self.admin_user = StaffUserFactory(username="admin", email="admin@example.com")
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
            "booking_reference": self.service_booking_paid.service_booking_reference,
            "reason": "Customer requested service refund.",
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
        self.assertEqual(refund_request.amount_to_refund, Decimal("250.00"))
        self.assertIsNotNone(refund_request.requested_at)
        self.assertEqual(RefundRequest.objects.count(), 1)

    def test_form_valid_data_create_sales(self):
        form_data = {
            "booking_reference": self.sales_booking_deposit.sales_booking_reference,
            "reason": "Customer cancelled sale.",
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
        self.assertEqual(refund_request.amount_to_refund, Decimal("100.00"))
        self.assertIsNotNone(refund_request.requested_at)
        self.assertEqual(RefundRequest.objects.count(), 1)

    def test_form_invalid_no_booking_selected(self):
        form_data = {
            "reason": "Test reason",
            "amount_to_refund": "100.00",
        }
        form = AdminRefundRequestForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("booking_reference", form.errors)
        self.assertEqual(
            form.errors["booking_reference"], ["This field is required."]
        )

    def test_form_initial_values_for_new_instance(self):
        form = AdminRefundRequestForm()
        self.assertIsNone(form.initial.get("is_admin_initiated"))
        self.assertIsNone(form.initial.get("status"))

    def test_form_edit_instance_service_booking(self):
        existing_refund_request = RefundRequestFactory(
            service_booking=self.service_booking_paid,
            payment=self.payment_succeeded_service,
            service_profile=self.service_profile,
            reason="Original service reason",
            amount_to_refund=Decimal("150.00"),
            is_admin_initiated=True,
            status="pending",
        )

        # No form_data for booking_reference, it should be populated by initial
        form = AdminRefundRequestForm(instance=existing_refund_request)
        self.assertEqual(form.initial["booking_reference"], self.service_booking_paid.service_booking_reference)

        # Now test with updated data
        form_data = {
            "booking_reference": self.service_booking_paid.service_booking_reference, # Must be included in data for POST
            "reason": "Updated service reason",
            "amount_to_refund": "200.00",
            "status": "pending", # Include status as it's a required field in the form
        }
        form = AdminRefundRequestForm(data=form_data, instance=existing_refund_request)
        self.assertTrue(form.is_valid(), f"Form is not valid: {form.errors}")

        updated_refund_request = form.save()
        self.assertEqual(updated_refund_request.pk, existing_refund_request.pk)
        self.assertEqual(updated_refund_request.reason, "Updated service reason")
        self.assertEqual(updated_refund_request.amount_to_refund, Decimal("200.00"))
        self.assertEqual(updated_refund_request.status, "pending")
        self.assertTrue(updated_refund_request.is_admin_initiated)
        self.assertEqual(RefundRequest.objects.count(), 1)

    def test_form_edit_instance_sales_booking(self):
        existing_refund_request = RefundRequestFactory(
            sales_booking=self.sales_booking_deposit,
            payment=self.payment_deposit_sales,
            sales_profile=self.sales_profile,
            reason="Original sales reason",
            amount_to_refund=Decimal("50.00"),
            is_admin_initiated=True,
            status="pending",
        )

        # No form_data for booking_reference, it should be populated by initial
        form = AdminRefundRequestForm(instance=existing_refund_request)
        self.assertEqual(form.initial["booking_reference"], self.sales_booking_deposit.sales_booking_reference)

        # Now test with updated data
        form_data = {
            "booking_reference": self.sales_booking_deposit.sales_booking_reference, # Must be included in data for POST
            "reason": "Updated sales reason",
            "amount_to_refund": "75.00",
            "status": "pending", # Include status as it's a required field in the form
        }
        form = AdminRefundRequestForm(data=form_data, instance=existing_refund_request)
        self.assertTrue(form.is_valid(), f"Form is not valid: {form.errors}")

        updated_refund_request = form.save()
        self.assertEqual(updated_refund_request.pk, existing_refund_request.pk)
        self.assertEqual(updated_refund_request.reason, "Updated sales reason")
        self.assertEqual(updated_refund_request.amount_to_refund, Decimal("75.00"))
        self.assertEqual(updated_refund_request.status, "pending")
        self.assertTrue(updated_refund_request.is_admin_initiated)
        self.assertEqual(RefundRequest.objects.count(), 1)
