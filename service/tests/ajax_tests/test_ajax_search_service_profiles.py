from django.test import TestCase, RequestFactory
from django.urls import reverse
import json


from users.tests.test_helpers.model_factories import UserFactory, StaffUserFactory
from service.tests.test_helpers.model_factories import ServiceProfileFactory


from service.ajax.ajax_search_service_profiles import search_customer_profiles_ajax


class AjaxSearchCustomerProfilesTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        # FIX 2: Create a staff user to attach to requests
        self.staff_user = StaffUserFactory()

        self.user1 = UserFactory(username="johndoe", email="john.doe@example.com")
        self.profile1 = ServiceProfileFactory(
            user=self.user1,
            name="John Doe",
            email="john.doe@example.com",
            phone_number="0412345678",
            city="Sydney",
            post_code="2000",
        )

        self.user2 = UserFactory(username="janedoe", email="jane.doe@test.com")
        self.profile2 = ServiceProfileFactory(
            user=self.user2,
            name="Jane Smith",
            email="jane.smith@example.com",
            phone_number="0498765432",
            city="Melbourne",
            address_line_1="123 Main St",
        )

        self.user3 = UserFactory(username="bobjohnson", email="bob.j@other.com")
        self.profile3 = ServiceProfileFactory(
            user=self.user3,
            name="Bob Johnson",
            email="bob.j@other.com",
            phone_number="0455551111",
            city="Sydney",
            country="Australia",
        )

        self.user4 = UserFactory(username="alice", email="alice@unique.com")
        self.profile4 = ServiceProfileFactory(
            user=self.user4,
            name="Alice Wonderland",
            email="alice@unique.com",
            phone_number="0400000000",
            city="Brisbane",
        )

    def test_search_customer_profiles_by_name(self):
        search_term = "John Doe"
        url = reverse("service:admin_api_search_customer") + f"?query={search_term}"
        request = self.factory.get(url)
        # FIX 3: Manually attach the user to the request
        request.user = self.staff_user
        response = search_customer_profiles_ajax(request)

        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEqual(len(content["profiles"]), 1)
        self.assertEqual(content["profiles"][0]["name"], self.profile1.name)

    def test_search_customer_profiles_by_email(self):
        search_term = "jane.doe@test.com"
        url = reverse("service:admin_api_search_customer") + f"?query={search_term}"
        request = self.factory.get(url)
        # FIX 3: Manually attach the user to the request
        request.user = self.staff_user
        response = search_customer_profiles_ajax(request)

        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEqual(len(content["profiles"]), 1)
        self.assertEqual(content["profiles"][0]["name"], self.profile2.name)

    def test_search_customer_profiles_by_phone_number(self):
        search_term = "045555"
        url = reverse("service:admin_api_search_customer") + f"?query={search_term}"
        request = self.factory.get(url)
        # FIX 3: Manually attach the user to the request
        request.user = self.staff_user
        response = search_customer_profiles_ajax(request)

        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEqual(len(content["profiles"]), 1)
        self.assertEqual(content["profiles"][0]["name"], self.profile3.name)

    def test_search_customer_profiles_multiple_matches_and_ordering(self):
        search_term = "Sydney"
        url = reverse("service:admin_api_search_customer") + f"?query={search_term}"
        request = self.factory.get(url)
        # FIX 3: Manually attach the user to the request
        request.user = self.staff_user
        response = search_customer_profiles_ajax(request)

        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEqual(len(content["profiles"]), 2)
        # Note: ordering is by name, so Bob Johnson comes before John Doe
        self.assertEqual(content["profiles"][0]["name"], self.profile3.name)
        self.assertEqual(content["profiles"][1]["name"], self.profile1.name)

    def test_search_customer_profiles_no_matches(self):
        search_term = "NonExistentCustomer"
        url = reverse("service:admin_api_search_customer") + f"?query={search_term}"
        request = self.factory.get(url)
        # FIX 3: Manually attach the user to the request
        request.user = self.staff_user
        response = search_customer_profiles_ajax(request)

        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEqual(len(content["profiles"]), 0)

    def test_search_customer_profiles_empty_query(self):
        url = reverse("service:admin_api_search_customer") + "?query="
        request = self.factory.get(url)
        # FIX 3: Manually attach the user to the request
        request.user = self.staff_user
        response = search_customer_profiles_ajax(request)

        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEqual(len(content["profiles"]), 0)

    def test_search_customer_profiles_no_query_parameter(self):
        url = reverse("service:admin_api_search_customer")
        request = self.factory.get(url)
        # FIX 3: Manually attach the user to the request
        request.user = self.staff_user
        response = search_customer_profiles_ajax(request)

        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content)
        self.assertEqual(len(content["profiles"]), 0)

    def test_only_get_requests_allowed(self):
        url = reverse("service:admin_api_search_customer")
        request = self.factory.post(url)
        # FIX 3: Manually attach the user to the request
        request.user = self.staff_user

        response = search_customer_profiles_ajax(request)
        self.assertEqual(response.status_code, 405)
