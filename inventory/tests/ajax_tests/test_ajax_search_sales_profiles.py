import json
from django.test import TestCase, RequestFactory
from django.urls import reverse
from inventory.ajax.ajax_search_sales_profiles import search_sales_profiles_ajax
from ..test_helpers.model_factories import UserFactory, SalesProfileFactory


class AjaxSearchSalesProfilesTest(TestCase):

    @classmethod
    def setUpTestData(cls):

        cls.factory = RequestFactory()
        cls.staff_user = UserFactory(is_staff=True)
        cls.non_staff_user = UserFactory(is_staff=False)

        cls.profile1 = SalesProfileFactory(
            name="Johnathan Doe",
            email="john.doe@example.com",
            phone_number="111-222-3333",
        )
        cls.profile2 = SalesProfileFactory(
            name="Alice Williams",
            email="alice.w@email.com",
            phone_number="444-555-6666",
        )
        cls.profile3 = SalesProfileFactory(
            name="Peter Jones",
            email="peter.j@test.com",
            phone_number="777-888-9999",
            address_line_1="123 Test Street",
        )

    def _get_response(self, user, query_params={}):

        request = self.factory.get(
            reverse("inventory:admin_api_search_sales_profiles"), query_params
        )
        request.user = user
        return search_sales_profiles_ajax(request)

    def test_view_requires_staff_user(self):
        response = self._get_response(self.non_staff_user, {"query": "John"})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(json.loads(response.content), {"status": "error", "message": "Admin access required."})

    def test_search_returns_correct_json_structure(self):

        response = self._get_response(self.staff_user, {"query": "Johnathan"})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn("profiles", data)

        self.assertEqual(len(data["profiles"]), 1)

        profile_data = data["profiles"][0]
        expected_keys = ["id", "name", "email", "phone_number"]
        for key in expected_keys:
            self.assertIn(key, profile_data)

    def test_search_by_name(self):
        response = self._get_response(self.staff_user, {"query": "williams"})
        data = json.loads(response.content)
        self.assertEqual(len(data["profiles"]), 1)
        self.assertEqual(data["profiles"][0]["id"], self.profile2.pk)

    def test_search_by_email(self):
        response = self._get_response(self.staff_user, {"query": "peter.j@test.com"})
        data = json.loads(response.content)
        self.assertEqual(len(data["profiles"]), 1)
        self.assertEqual(data["profiles"][0]["id"], self.profile3.pk)

    def test_search_by_phone_number(self):
        response = self._get_response(self.staff_user, {"query": "111-222"})
        data = json.loads(response.content)
        self.assertEqual(len(data["profiles"]), 1)
        self.assertEqual(data["profiles"][0]["id"], self.profile1.pk)

    def test_search_by_address(self):
        response = self._get_response(self.staff_user, {"query": "Test Street"})
        data = json.loads(response.content)
        self.assertEqual(len(data["profiles"]), 1)
        self.assertEqual(data["profiles"][0]["id"], self.profile3.pk)

    def test_search_with_no_query_returns_empty_list(self):
        response = self._get_response(self.staff_user, {"query": ""})
        data = json.loads(response.content)
        self.assertEqual(len(data["profiles"]), 0)

    def test_search_returns_distinct_results(self):

        SalesProfileFactory(name="Xavier Jones", email="x.jones@example.com")

        response = self._get_response(self.staff_user, {"query": "Jones"})
        data = json.loads(response.content)

        self.assertEqual(len(data["profiles"]), 2)

        ids = [p["id"] for p in data["profiles"]]
        self.assertEqual(ids.count(self.profile3.pk), 1)
