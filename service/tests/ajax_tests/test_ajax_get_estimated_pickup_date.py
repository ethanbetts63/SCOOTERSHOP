from django.test import TestCase, Client
from django.urls import reverse
from unittest.mock import patch
import datetime
from users.tests.test_helpers.model_factories import UserFactory, StaffUserFactory 
from service.tests.test_helpers.model_factories import ServiceBookingFactory, ServiceProfileFactory, ServiceTypeFactory, ServiceSettingsFactory, ServiceTermsFactory, ServicefaqFactory
from inventory.tests.test_helpers.model_factories import SalesBookingFactory, SalesProfileFactory
from payments.tests.test_helpers.model_factories import PaymentFactory
from payments.tests.test_helpers.model_factories import WebhookEventFactory
from refunds.tests.test_helpers.model_factories import RefundRequestFactory, RefundSettingsFactory

class AjaxGetEstimatedPickupDateTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.url = reverse("service:admin_api_get_estimated_pickup_date")

        # FIX 2: Create a staff user and log them in
        self.staff_user = StaffUserFactory()
        self.client.force_login(self.staff_user)

        self.service_type = ServiceTypeFactory(estimated_duration=3)
        self.service_type_zero_duration = ServiceTypeFactory(estimated_duration=0)
        self.test_service_date = datetime.date(2025, 10, 20)

    def test_valid_request(self):
        response = self.client.get(
            self.url,
            {
                "service_type_id": self.service_type.pk,
                "service_date": self.test_service_date.strftime("%Y-%m-%d"),
            },
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        expected_pickup_date = self.test_service_date + datetime.timedelta(
            days=self.service_type.estimated_duration
        )
        self.assertEqual(
            data["estimated_pickup_date"], expected_pickup_date.strftime("%Y-%m-%d")
        )

    def test_valid_request_zero_duration(self):
        response = self.client.get(
            self.url,
            {
                "service_type_id": self.service_type_zero_duration.pk,
                "service_date": self.test_service_date.strftime("%Y-%m-%d"),
            },
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(
            data["estimated_pickup_date"], self.test_service_date.strftime("%Y-%m-%d")
        )

    def test_missing_service_type_id(self):
        response = self.client.get(
            self.url, {"service_date": self.test_service_date.strftime("%Y-%m-%d")}
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data["error"], "Missing service_type_id or service_date")

    def test_missing_service_date(self):
        response = self.client.get(self.url, {"service_type_id": self.service_type.pk})
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data["error"], "Missing service_type_id or service_date")

    def test_service_type_not_found(self):
        non_existent_id = self.service_type.pk + 999
        response = self.client.get(
            self.url,
            {
                "service_type_id": non_existent_id,
                "service_date": self.test_service_date.strftime("%Y-%m-%d"),
            },
        )
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertEqual(data["error"], "ServiceType not found")

    def test_invalid_date_format(self):
        response = self.client.get(
            self.url,
            {"service_type_id": self.service_type.pk, "service_date": "2025/10/20"},
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data["error"], "Invalid date format. ExpectedYYYY-MM-DD.")

    @patch(
        "service.ajax.ajax_get_estimated_pickup_date.calculate_estimated_pickup_date"
    )
    def test_calculate_estimated_pickup_date_utility_error(self, mock_calculate):
        mock_calculate.return_value = None
        response = self.client.get(
            self.url,
            {
                "service_type_id": self.service_type.pk,
                "service_date": self.test_service_date.strftime("%Y-%m-%d"),
            },
        )
        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertEqual(data["error"], "Could not calculate estimated pickup date")

    @patch("service.models.ServiceType.objects.get")
    def test_unexpected_exception(self, mock_get_service_type):
        mock_get_service_type.side_effect = Exception("Database connection error")
        response = self.client.get(
            self.url,
            {
                "service_type_id": self.service_type.pk,
                "service_date": self.test_service_date.strftime("%Y-%m-%d"),
            },
        )
        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertEqual(
            data["error"], "An unexpected error occurred: Database connection error"
        )
