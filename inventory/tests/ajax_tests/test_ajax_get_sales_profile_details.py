import json
from django.test import TestCase, RequestFactory
from django.urls import reverse
from inventory.ajax.ajax_get_sales_profile_details import get_sales_profile_details_ajax
from inventory.tests.test_helpers.model_factories import SalesProfileFactory
from users.tests.test_helpers.model_factories import UserFactory, StaffUserFactory


class GetSalesProfileDetailsAjaxTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.admin_user = StaffUserFactory()
        self.non_admin_user = UserFactory()
        self.sales_profile = SalesProfileFactory()

    def test_get_sales_profile_details_ajax_as_admin(self):
        request = self.factory.get(
            reverse(
                "inventory:admin_api_get_sales_profile_details",
                kwargs={"pk": self.sales_profile.pk},
            )
        )
        request.user = self.admin_user
        response = get_sales_profile_details_ajax(request, self.sales_profile.pk)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["profile_details"]["id"], self.sales_profile.pk)
        self.assertEqual(data["profile_details"]["name"], self.sales_profile.name)

    def test_get_sales_profile_details_ajax_as_non_admin(self):
        request = self.factory.get(
            reverse(
                "inventory:admin_api_get_sales_profile_details",
                kwargs={"pk": self.sales_profile.pk},
            )
        )
        request.user = self.non_admin_user
        response = get_sales_profile_details_ajax(request, self.sales_profile.pk)
        self.assertEqual(response.status_code, 403)
        data = json.loads(response.content)
        self.assertEqual(data, {"status": "error", "message": "Admin access required."})

    def test_get_sales_profile_details_ajax_not_found(self):
        request = self.factory.get(
            reverse("inventory:admin_api_get_sales_profile_details", kwargs={"pk": 999})
        )
        request.user = self.admin_user
        response = get_sales_profile_details_ajax(request, 999)
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.content)
        self.assertIn("Sales Profile not found", data["error"])
