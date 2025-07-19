
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.messages import get_messages
from users.tests.test_helpers.model_factories import UserFactory
from refunds.tests.test_helpers.model_factories import RefundRequestFactory
from service.tests.test_helpers.model_factories import ServiceBookingFactory
from inventory.tests.test_helpers.model_factories import SalesBookingFactory

class AdminCreateRefundRequestViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = UserFactory(is_staff=True, is_superuser=True)
        self.client.force_login(self.admin_user)
        self.create_url = reverse("refunds:admin_create_refund_request")

    def test_get_create_refund_request_view(self):
        response = self.client.get(self.create_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "refunds/admin_create_refund_form.html")
        self.assertIn("form", response.context)

    def test_create_refund_request_for_service_booking_successfully(self):
        service_booking = ServiceBookingFactory()
        form_data = {
            "service_booking": service_booking.id,
            "reason": "Test reason",
            "amount_to_refund": "100.00",
            "request_email": "test@example.com",
        }
        response = self.client.post(self.create_url, form_data, follow=True)
        self.assertEqual(response.status_code, 200)
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), f"Refund Request for booking '{service_booking.service_booking_reference}' created successfully! Current Status: Reviewed Pending Approval")

    def test_create_refund_request_for_sales_booking_successfully(self):
        sales_booking = SalesBookingFactory()
        form_data = {
            "sales_booking": sales_booking.id,
            "reason": "Test reason",
            "amount_to_refund": "200.00",
            "request_email": "test2@example.com",
        }
        response = self.client.post(self.create_url, form_data, follow=True)
        self.assertEqual(response.status_code, 200)
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), f"Refund Request for booking '{sales_booking.sales_booking_reference}' created successfully! Current Status: Reviewed Pending Approval")

    def test_create_refund_request_invalid_form(self):
        form_data = {"reason": ""}  # Invalid data
        response = self.client.post(self.create_url, form_data)
        self.assertEqual(response.status_code, 200)
        self.assertIn("form", response.context)
        self.assertTrue(response.context["form"].errors)
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Please correct the errors below.")
