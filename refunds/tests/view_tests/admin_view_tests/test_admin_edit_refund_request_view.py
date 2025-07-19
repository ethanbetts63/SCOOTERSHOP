
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.messages import get_messages
from users.tests.test_helpers.model_factories import UserFactory
from refunds.tests.test_helpers.model_factories import RefundRequestFactory
from service.tests.test_helpers.model_factories import ServiceBookingFactory

class AdminEditRefundRequestViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = UserFactory(is_staff=True, is_superuser=True)
        self.client.force_login(self.admin_user)
        self.service_booking = ServiceBookingFactory(payment__status='succeeded')
        self.refund_request = RefundRequestFactory(service_booking=self.service_booking)
        self.edit_url = reverse("refunds:edit_refund_request", kwargs={"pk": self.refund_request.pk})

    def test_get_edit_refund_request_view(self):
        response = self.client.get(self.edit_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "refunds/admin_edit_refund_form.html")
        self.assertIn("form", response.context)

    def test_edit_refund_request_successfully(self):
        form_data = {
            "booking_reference": self.service_booking.service_booking_reference,
            "reason": "Updated reason",
            "amount_to_refund": "150.00",
            "status": "approved",
            "request_email": self.refund_request.request_email
        }
        response = self.client.post(self.edit_url, form_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.refund_request.refresh_from_db()
        self.assertEqual(self.refund_request.reason, "Updated reason")
        self.assertEqual(self.refund_request.status, "approved")
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertIn("updated successfully!", str(messages[0]))

    def test_edit_refund_request_invalid_form(self):
        form_data = {"reason": ""}  # Invalid data
        response = self.client.post(self.edit_url, form_data)
        self.assertEqual(response.status_code, 200)
        self.assertIn("form", response.context)
        self.assertTrue(response.context["form"].errors)
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Please correct the errors below.")
