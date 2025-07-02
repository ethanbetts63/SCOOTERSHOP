from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.http import JsonResponse
import json


from ..test_helpers.model_factories import ServiceProfileFactory, UserFactory


from service.ajax.ajax_get_service_profile_details import (
    get_service_profile_details_ajax,
)


class AjaxGetServiceProfileDetailsTest(TestCase):

    def setUp(self):

        self.factory = RequestFactory()

        self.user = UserFactory()

        self.service_profile = ServiceProfileFactory(user=self.user)

    def test_get_service_profile_details_success(self):

        url = reverse(
            "service:admin_api_get_customer_details", args=[self.service_profile.pk]
        )
        request = self.factory.get(url)

        response = get_service_profile_details_ajax(
            request, profile_id=self.service_profile.pk
        )

        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response, JsonResponse)
        content = json.loads(response.content)

        expected_details = {
            "id": self.service_profile.pk,
            "name": self.service_profile.name,
            "email": self.service_profile.email,
            "phone_number": self.service_profile.phone_number,
            "address_line_1": self.service_profile.address_line_1,
            "address_line_2": self.service_profile.address_line_2,
            "city": self.service_profile.city,
            "state": self.service_profile.state,
            "post_code": self.service_profile.post_code,
            "country": self.service_profile.country,
            "user_id": self.service_profile.user.pk,
            "username": self.service_profile.user.username,
        }
        self.assertIn("profile_details", content)
        self.assertEqual(content["profile_details"], expected_details)

    def test_get_service_profile_details_not_found(self):

        invalid_profile_id = self.service_profile.pk + 100

        url = reverse(
            "service:admin_api_get_customer_details", args=[invalid_profile_id]
        )
        request = self.factory.get(url)

        response = get_service_profile_details_ajax(
            request, profile_id=invalid_profile_id
        )

        self.assertEqual(response.status_code, 404)
        self.assertIsInstance(response, JsonResponse)
        content = json.loads(response.content)
        self.assertIn("error", content)
        self.assertIn("ServiceProfile not found or invalid ID", content["error"])

    def test_only_get_requests_allowed(self):

        test_profile_id = 1

        url = reverse("service:admin_api_get_customer_details", args=[test_profile_id])
        request = self.factory.post(url)

        response = get_service_profile_details_ajax(request, profile_id=test_profile_id)

        self.assertEqual(response.status_code, 405)
