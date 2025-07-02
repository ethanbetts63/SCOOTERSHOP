from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.http import JsonResponse
import json


from ..test_helpers.model_factories import (
    CustomerMotorcycleFactory,
    ServiceProfileFactory,
)


from service.ajax.ajax_get_customer_motorcycle_details import (
    get_motorcycle_details_ajax,
)


class AjaxGetCustomerMotorcycleDetailsTest(TestCase):

    def setUp(self):

        self.factory = RequestFactory()

        self.service_profile = ServiceProfileFactory()

        self.motorcycle = CustomerMotorcycleFactory(
            service_profile=self.service_profile
        )

    def test_get_motorcycle_details_success(self):

        url = reverse(
            "service:admin_api_get_motorcycle_details", args=[self.motorcycle.pk]
        )
        request = self.factory.get(url)

        response = get_motorcycle_details_ajax(
            request, motorcycle_id=self.motorcycle.pk
        )

        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response, JsonResponse)
        content = json.loads(response.content)

        expected_details = {
            "id": self.motorcycle.pk,
            "brand": self.motorcycle.brand,
            "model": self.motorcycle.model,
            "year": int(self.motorcycle.year),
            "engine_size": self.motorcycle.engine_size,
            "rego": self.motorcycle.rego,
            "vin_number": self.motorcycle.vin_number,
            "odometer": self.motorcycle.odometer,
            "transmission": self.motorcycle.transmission,
            "engine_number": self.motorcycle.engine_number,
        }
        self.assertIn("motorcycle_details", content)
        self.assertEqual(content["motorcycle_details"], expected_details)

    def test_get_motorcycle_details_not_found(self):

        invalid_motorcycle_id = self.motorcycle.pk + 100

        url = reverse(
            "service:admin_api_get_motorcycle_details", args=[invalid_motorcycle_id]
        )
        request = self.factory.get(url)

        response = get_motorcycle_details_ajax(
            request, motorcycle_id=invalid_motorcycle_id
        )

        self.assertEqual(response.status_code, 404)
        self.assertIsInstance(response, JsonResponse)
        content = json.loads(response.content)
        self.assertIn("error", content)
        self.assertIn("Motorcycle not found or invalid ID", content["error"])

    def test_only_get_requests_allowed(self):

        url = reverse(
            "service:admin_api_get_motorcycle_details", args=[self.motorcycle.pk]
        )

        request = self.factory.post(url)
        response = get_motorcycle_details_ajax(
            request, motorcycle_id=self.motorcycle.pk
        )

        self.assertEqual(response.status_code, 405)
