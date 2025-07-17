from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.http import JsonResponse
import json
from unittest.mock import patch, Mock
from datetime import date, timedelta
from django.utils import timezone
from service.ajax.ajax_admin_booking_precheck import admin_booking_precheck_ajax
from users.tests.test_helpers.model_factories import UserFactory, StaffUserFactory
from service.tests.test_helpers.model_factories import ServiceBookingFactory, ServiceProfileFactory, ServiceTypeFactory, ServiceSettingsFactory, ServiceTermsFactory, ServicefaqFactory, CustomerMotorcycleFactory, BlockedServiceDateFactory, ServiceBrandFactory
from inventory.tests.test_helpers.model_factories import SalesBookingFactory, SalesProfileFactory
from payments.tests.test_helpers.model_factories import PaymentFactory, WebhookEventFactory
from refunds.tests.test_helpers.model_factories import RefundRequestFactory, RefundSettingsFactory

class AjaxAdminBookingPrecheckTest(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.service_type = ServiceTypeFactory()
        self.staff_user = StaffUserFactory()

        today = date.today()
        future_date = today + timedelta(days=5)
        current_time = (
            timezone.localtime(timezone.now()) + timedelta(minutes=10)
        ).time()

        self.valid_form_data = {
            "service_type": self.service_type.pk,
            "service_date": future_date.strftime("%Y-%m-%d"),
            "dropoff_date": future_date.strftime("%Y-%m-%d"),
            "dropoff_time": current_time.strftime("%H:%M"),
            "booking_status": "pending",
            "payment_status": "unpaid",
            "customer_notes": "Some notes",
            "admin_notes": "Internal notes",
            "estimated_pickup_date": (future_date + timedelta(days=2)).strftime(
                "%Y-%m-%d"
            ),
        }

    @patch("service.ajax.ajax_admin_booking_precheck.AdminBookingDetailsForm")
    def test_precheck_success_no_warnings(self, MockAdminBookingDetailsForm):
        mock_form_instance = Mock()
        mock_form_instance.is_valid.return_value = True
        mock_form_instance.get_warnings.return_value = []
        MockAdminBookingDetailsForm.return_value = mock_form_instance

        url = reverse("service:admin_api_booking_precheck")
        request = self.factory.post(url, self.valid_form_data)
        # FIX: Manually attach the user to the request
        request.user = self.staff_user

        response = admin_booking_precheck_ajax(request)

        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response, JsonResponse)
        content = json.loads(response.content)

        self.assertEqual(content["status"], "success")

    @patch("service.ajax.ajax_admin_booking_precheck.AdminBookingDetailsForm")
    def test_precheck_success_with_warnings(self, MockAdminBookingDetailsForm):
        mock_form_instance = Mock()
        mock_form_instance.is_valid.return_value = True
        mock_form_instance.get_warnings.return_value = [
            "Warning: Service date is in the past.",
        ]
        MockAdminBookingDetailsForm.return_value = mock_form_instance

        url = reverse("service:admin_api_booking_precheck")
        request = self.factory.post(url, self.valid_form_data)
        # FIX: Manually attach the user to the request
        request.user = self.staff_user

        response = admin_booking_precheck_ajax(request)

        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEqual(content["status"], "warnings")
        self.assertIn("Warning: Service date is in the past.", content["warnings"])

    @patch("service.ajax.ajax_admin_booking_precheck.AdminBookingDetailsForm")
    def test_precheck_form_errors(self, MockAdminBookingDetailsForm):
        mock_form_instance = Mock()
        mock_form_instance.is_valid.return_value = False
        mock_form_instance.errors.as_json.return_value = json.dumps(
            {"service_type": [{"message": "This field is required."}]}
        )
        MockAdminBookingDetailsForm.return_value = mock_form_instance

        url = reverse("service:admin_api_booking_precheck")
        request = self.factory.post(url, {})
        # FIX: Manually attach the user to the request
        request.user = self.staff_user

        response = admin_booking_precheck_ajax(request)

        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEqual(content["status"], "errors")

    def test_only_post_requests_allowed(self):
        url = reverse("service:admin_api_booking_precheck")
        request = self.factory.get(url)
        # FIX: Manually attach the user to the request
        request.user = self.staff_user
        
        response = admin_booking_precheck_ajax(request)
        # The @require_POST decorator runs before the @admin_required decorator
        self.assertEqual(response.status_code, 405)
