from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
import json
from unittest.mock import patch


from users.tests.test_helpers.model_factories import UserFactory, StaffUserFactory

User = get_user_model()


class DashboardAdminAjaxPermissionsTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        cls.regular_user = UserFactory()
        cls.staff_user = StaffUserFactory()

    def _test_ajax_permissions(self, url_name, kwargs=None, method="get", data=None):
        if data is None:
            data = {}
        url = reverse(url_name, kwargs=kwargs)

        # Test anonymous user
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

        # Test regular user
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

        # Test staff user
        self.client.login(username=self.staff_user.username, password="password123")
        with patch("dashboard.ajax.search_google_reviews.requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {
                "result": {"reviews": []},
                "status": "OK",
            }
            response_staff = self.client.generic(method.upper(), url, data)
        self.assertIn(
            response_staff.status_code,
            [200, 400, 500],
            f"URL {url} did not return 200, 400, or 500 for staff user.",
        )
        self.client.logout()

    def test_admin_ajax_endpoints_permissions(self):
        self._test_ajax_permissions(
            "dashboard:search_google_reviews_ajax", data={"query": "test"}
        )
