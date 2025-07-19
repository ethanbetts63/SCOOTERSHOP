from django.test import TestCase, Client
from django.urls import reverse
from decimal import Decimal

from refunds.models import RefundRequest
from users.tests.test_helpers.model_factories import StaffUserFactory
from inventory.tests.test_helpers.model_factories import SalesBookingFactory, SalesProfileFactory, MotorcycleFactory
from service.tests.test_helpers.model_factories import ServiceBookingFactory, ServiceProfileFactory, CustomerMotorcycleFactory, ServiceTypeFactory
from payments.tests.test_helpers.model_factories import PaymentFactory


class AdminCreateRefundRequestViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = StaffUserFactory(username="admin", email="admin@example.com")
        self.create_url = reverse("refunds:add_refund_request")

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

    def test_get_request_renders_form(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(self.create_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "refunds/admin_create_refund_form.html")
        self.assertIn('form', response.context)
        self.assertFalse(response.context['form'].is_bound)

    def test_post_request_create_service_refund_valid_data(self):
        self.client.force_login(self.admin_user)
        form_data = {
            "booking_reference": self.service_booking.service_booking_reference,
            "reason": "Customer changed mind",
            "amount_to_refund": "50.00",
            "status": "reviewed_pending_approval",
        }
        response = self.client.post(self.create_url, form_data)
        self.assertEqual(response.status_code, 302)  # Redirects on success
        self.assertRedirects(response, reverse("refunds:admin_refund_management"))
        self.assertEqual(RefundRequest.objects.count(), 1)
        refund_request = RefundRequest.objects.first()
        self.assertEqual(refund_request.service_booking, self.service_booking)
        self.assertEqual(refund_request.amount_to_refund, Decimal("50.00"))
        self.assertEqual(refund_request.status, "reviewed_pending_approval")
        self.assertTrue(refund_request.is_admin_initiated)

    def test_post_request_create_sales_refund_valid_data(self):
        self.client.force_login(self.admin_user)
        form_data = {
            "booking_reference": self.sales_booking.sales_booking_reference,
            "reason": "Product returned",
            "amount_to_refund": "150.00",
            "status": "reviewed_pending_approval",
        }
        response = self.client.post(self.create_url, form_data)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("refunds:admin_refund_management"))
        self.assertEqual(RefundRequest.objects.count(), 1)
        refund_request = RefundRequest.objects.first()
        self.assertEqual(refund_request.sales_booking, self.sales_booking)
        self.assertEqual(refund_request.amount_to_refund, Decimal("150.00"))
        self.assertEqual(refund_request.status, "reviewed_pending_approval")
        self.assertTrue(refund_request.is_admin_initiated)

    def test_post_request_invalid_data(self):
        self.client.force_login(self.admin_user)
        form_data = {
            "booking_reference": "INVALIDREF",  # Invalid booking reference
            "reason": "Test",
            "amount_to_refund": "10.00",
            "status": "reviewed_pending_approval",
        }
        response = self.client.post(self.create_url, form_data)
        self.assertEqual(response.status_code, 200)  # Stays on page with errors
        self.assertTemplateUsed(response, "refunds/admin_create_refund_form.html")
        self.assertIn('form', response.context)
        self.assertTrue(response.context['form'].is_bound)
        self.assertFalse(response.context['form'].is_valid())
        self.assertIn('booking_reference', response.context['form'].errors)
        self.assertEqual(RefundRequest.objects.count(), 0)

    def test_post_request_missing_required_fields(self):
        self.client.force_login(self.admin_user)
        form_data = {
            "booking_reference": "",  # Missing required field
            "amount_to_refund": "", # Missing required field
        }
        response = self.client.post(self.create_url, form_data)
        self.assertEqual(response.status_code, 200)
        self.assertIn('booking_reference', response.context['form'].errors)
        self.assertIn('amount_to_refund', response.context['form'].errors)
        self.assertEqual(RefundRequest.objects.count(), 0)

    def test_unauthenticated_access_redirects_to_login(self):
        response = self.client.get(self.create_url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("users:login") + "?next=" + self.create_url)

    def test_non_staff_user_access_redirects_with_message(self):
        non_staff_user = StaffUserFactory(is_staff=False)
        self.client.force_login(non_staff_user)
        response = self.client.get(self.create_url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("users:login") + "?next=" + self.create_url) # Should redirect to login due to AdminRequiredMixin
