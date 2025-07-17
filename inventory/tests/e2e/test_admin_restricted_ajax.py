from django.test import TestCase, Client
from django.urls import reverse
import json
from users.tests.test_helpers.model_factories import UserFactory, StaffUserFactory
from inventory.tests.test_helpers.model_factories import (
    MotorcycleFactory,
    SalesProfileFactory,
    SalesBookingFactory,
)


class InventoryAdminAjaxPermissionsTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        cls.regular_user = UserFactory(password="password123")
        cls.staff_user = StaffUserFactory()
        cls.motorcycle = MotorcycleFactory()
        cls.sales_profile = SalesProfileFactory()
        cls.sales_booking = SalesBookingFactory()

    def _test_ajax_permissions(self, url_name, kwargs=None, method="get", data=None):
        if data is None:
            data = {}
        url = reverse(url_name, kwargs=kwargs)

        response_anon = self.client.generic(method.upper(), url, data)
        self.assertEqual(
            response_anon.status_code,
            401,
            f"URL {url} did not return 401 for anonymous user.",
        )
        self.assertEqual(
            json.loads(response_anon.content),
            {"status": "error", "message": "Authentication required."},
        )

        self.client.login(username=self.regular_user.username, password="password123")
        response_regular = self.client.generic(method.upper(), url, data)
        self.assertEqual(
            response_regular.status_code,
            403,
            f"URL {url} did not return 403 for regular user.",
        )
        self.assertEqual(
            json.loads(response_regular.content),
            {"status": "error", "message": "Admin access required."},
        )
        self.client.logout()

        self.client.login(username=self.staff_user.username, password="password123")
        response_staff = self.client.generic(method.upper(), url, data)
        self.assertIn(
            response_staff.status_code,
            [200, 400],
            f"URL {url} did not return 200 or 400 for staff user.",
        )
        self.client.logout()

    def test_admin_ajax_endpoints_permissions(self):
        self._test_ajax_permissions(
            "inventory:admin_api_search_motorcycles", data={"query": "test"}
        )
        self._test_ajax_permissions(
            "inventory:admin_api_get_motorcycle_details",
            kwargs={"pk": self.motorcycle.pk},
        )
        self._test_ajax_permissions(
            "inventory:admin_api_search_sales_profiles", data={"query": "test"}
        )
        self._test_ajax_permissions(
            "inventory:admin_api_get_sales_profile_details",
            kwargs={"pk": self.sales_profile.pk},
        )
        self._test_ajax_permissions(
            "inventory:admin_api_sales_booking_precheck", method="post", data={}
        )
        self._test_ajax_permissions("inventory:get_sales_bookings_json")
        self._test_ajax_permissions(
            "inventory:admin_api_search_sales_bookings", data={"query": "test"}
        )
