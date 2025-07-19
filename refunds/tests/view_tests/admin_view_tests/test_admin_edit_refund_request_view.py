from django.test import TestCase, Client
from django.urls import reverse
from decimal import Decimal

from refunds.models import RefundRequest
from refunds.tests.test_helpers.model_factories import RefundRequestFactory
from users.tests.test_helpers.model_factories import StaffUserFactory
from inventory.tests.test_helpers.model_factories import SalesBookingFactory, SalesProfileFactory, MotorcycleFactory
from service.tests.test_helpers.model_factories import ServiceBookingFactory, ServiceProfileFactory, CustomerMotorcycleFactory, ServiceTypeFactory
from payments.tests.test_helpers.model_factories import PaymentFactory


class AdminEditRefundRequestViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = StaffUserFactory(username="admin", email="admin@example.com")

        # Setup for service booking
        self.service_profile = ServiceProfileFactory()
        self.customer_motorcycle = CustomerMotorcycleFactory(service_profile=self.service_profile)
        self.service_type = ServiceTypeFactory()
        self.service_payment = PaymentFactory(
            amount=Decimal("100.00"),
            status="succeeded",
            service_customer_profile=self.service_profile
        )
        self.service_booking = ServiceBookingFactory(
            service_profile=self.service_profile,
            customer_motorcycle=self.customer_motorcycle,
            service_type=self.service_type,
            payment=self.service_payment,
            amount_paid=self.service_payment.amount,
            calculated_total=self.service_payment.amount,
            payment_status="paid",
            booking_status="confirmed",
        )
        self.service_payment.service_booking = self.service_booking
        self.service_payment.save()

        # Setup for sales booking
        self.sales_profile = SalesProfileFactory()
        self.motorcycle = MotorcycleFactory()
        self.sales_payment = PaymentFactory(
            amount=Decimal("200.00"),
            status="succeeded",
            sales_customer_profile=self.sales_profile
        )
        self.sales_booking = SalesBookingFactory(
            sales_profile=self.sales_profile,
            motorcycle=self.motorcycle,
            payment=self.sales_payment,
            amount_paid=self.sales_payment.amount,
            payment_status="paid",
            booking_status="confirmed",
        )
        self.sales_payment.sales_booking = self.sales_booking
        self.sales_payment.save()

        self.refund_request_service = RefundRequestFactory(
            service_booking=self.service_booking,
            payment=self.service_payment,
            service_profile=self.service_profile,
            amount_to_refund=Decimal("50.00"),
            status="pending",
            is_admin_initiated=True,
        )
        self.refund_request_sales = RefundRequestFactory(
            sales_booking=self.sales_booking,
            payment=self.sales_payment,
            sales_profile=self.sales_profile,
            amount_to_refund=Decimal("100.00"),
            status="pending",
            is_admin_initiated=True,
        )

    def test_get_request_renders_form_service_booking(self):
        self.client.force_login(self.admin_user)
        edit_url = reverse("refunds:edit_refund_request", kwargs={"pk": self.refund_request_service.pk})
        response = self.client.get(edit_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "refunds/admin_edit_refund_form.html")
        self.assertIn('form', response.context)
        self.assertTrue(response.context['form'].is_bound) # Form should be bound with instance data
        self.assertEqual(response.context['form'].instance, self.refund_request_service)
        self.assertEqual(response.context['form'].initial['booking_reference'], self.service_booking.service_booking_reference)

    def test_get_request_renders_form_sales_booking(self):
        self.client.force_login(self.admin_user)
        edit_url = reverse("refunds:edit_refund_request", kwargs={"pk": self.refund_request_sales.pk})
        response = self.client.get(edit_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "refunds/admin_edit_refund_form.html")
        self.assertIn('form', response.context)
        self.assertTrue(response.context['form'].is_bound)
        self.assertEqual(response.context['form'].instance, self.refund_request_sales)
        self.assertEqual(response.context['form'].initial['booking_reference'], self.sales_booking.sales_booking_reference)

    def test_post_request_update_service_refund_valid_data(self):
        self.client.force_login(self.admin_user)
        edit_url = reverse("refunds:edit_refund_request", kwargs={"pk": self.refund_request_service.pk})
        form_data = {
            "booking_reference": self.service_booking.service_booking_reference, # Must be included for POST
            "reason": "Updated service reason",
            "amount_to_refund": "75.00",
            "status": "approved",
        }
        response = self.client.post(edit_url, form_data)
        self.assertEqual(response.status_code, 302)  # Redirects on success
        self.assertRedirects(response, reverse("refunds:admin_refund_management"))

        updated_refund_request = RefundRequest.objects.get(pk=self.refund_request_service.pk)
        self.assertEqual(updated_refund_request.reason, "Updated service reason")
        self.assertEqual(updated_refund_request.amount_to_refund, Decimal("75.00"))
        self.assertEqual(updated_refund_request.status, "approved")

    def test_post_request_update_sales_refund_valid_data(self):
        self.client.force_login(self.admin_user)
        edit_url = reverse("refunds:edit_refund_request", kwargs={"pk": self.refund_request_sales.pk})
        form_data = {
            "booking_reference": self.sales_booking.sales_booking_reference, # Must be included for POST
            "reason": "Updated sales reason",
            "amount_to_refund": "120.00",
            "status": "refunded",
        }
        response = self.client.post(edit_url, form_data)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("refunds:admin_refund_management"))

        updated_refund_request = RefundRequest.objects.get(pk=self.refund_request_sales.pk)
        self.assertEqual(updated_refund_request.reason, "Updated sales reason")
        self.assertEqual(updated_refund_request.amount_to_refund, Decimal("120.00"))
        self.assertEqual(updated_refund_request.status, "refunded")

    def test_post_request_invalid_data(self):
        self.client.force_login(self.admin_user)
        edit_url = reverse("refunds:edit_refund_request", kwargs={"pk": self.refund_request_service.pk})
        form_data = {
            "booking_reference": "INVALIDREF",  # Invalid booking reference
            "amount_to_refund": "-10.00", # Invalid amount
            "status": "pending",
        }
        response = self.client.post(edit_url, form_data)
        self.assertEqual(response.status_code, 200)  # Stays on page with errors
        self.assertTemplateUsed(response, "refunds/admin_edit_refund_form.html")
        self.assertIn('form', response.context)
        self.assertTrue(response.context['form'].is_bound)
        self.assertFalse(response.context['form'].is_valid())
        self.assertIn('booking_reference', response.context['form'].errors)
        self.assertIn('amount_to_refund', response.context['form'].errors)

    def test_unauthenticated_access_redirects_to_login(self):
        edit_url = reverse("refunds:edit_refund_request", kwargs={"pk": self.refund_request_service.pk})
        response = self.client.get(edit_url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("users:login") + "?next=" + edit_url)

    def test_non_staff_user_access_redirects_with_message(self):
        non_staff_user = StaffUserFactory(is_staff=False)
        self.client.force_login(non_staff_user)
        edit_url = reverse("refunds:edit_refund_request", kwargs={"pk": self.refund_request_service.pk})
        response = self.client.get(edit_url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("users:login") + "?next=" + edit_url) # Should redirect to login due to AdminRequiredMixin
