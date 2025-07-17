from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.http import JsonResponse
import json


from users.tests.test_helpers.model_factories import StaffUserFactory
from service.tests.test_helpers.model_factories import (
    ServiceProfileFactory,
    CustomerMotorcycleFactory,
)


class AjaxGetCustomerMotorcyclesTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.service_profile = ServiceProfileFactory()

        self.motorcycle1 = CustomerMotorcycleFactory(
            service_profile=self.service_profile, brand="Honda"
        )
        self.motorcycle2 = CustomerMotorcycleFactory(
            service_profile=self.service_profile, brand="Yamaha"
        )

        self.staff_user = StaffUserFactory()
        self.client.force_login(self.staff_user)  # Using client login for simplicity

    def test_get_customer_motorcycles_success(self):
        url = reverse(
            "service:admin_api_customer_motorcycles", args=[self.service_profile.pk]
        )
        # Using the test client is simpler than RequestFactory when user is needed
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response, JsonResponse)
        content = json.loads(response.content)

        self.assertIn("motorcycles", content)
        self.assertEqual(len(content["motorcycles"]), 2)

        motorcycle_brands = {m["brand"] for m in content["motorcycles"]}
        self.assertIn("Honda", motorcycle_brands)
        self.assertIn("Yamaha", motorcycle_brands)

    def test_get_customer_motorcycles_profile_not_found(self):
        invalid_profile_id = self.service_profile.pk + 100
        url = reverse(
            "service:admin_api_customer_motorcycles", args=[invalid_profile_id]
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)
        self.assertIsInstance(response, JsonResponse)
        content = json.loads(response.content)
        self.assertIn("error", content)

        # FIX: Use assertIn to check for the key part of the message
        self.assertIn("ServiceProfile not found", content["error"])

    def test_only_get_requests_allowed(self):
        url = reverse(
            "service:admin_api_customer_motorcycles", args=[self.service_profile.pk]
        )
        response = self.client.post(url)

        # The @require_GET decorator returns 405 for other methods
        self.assertEqual(response.status_code, 405)
