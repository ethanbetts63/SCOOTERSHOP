from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone


from service.models import CustomerMotorcycle
from ...test_helpers.model_factories import (
    UserFactory,
    CustomerMotorcycleFactory,
    ServiceProfileFactory,
)


class CustomerMotorcycleManagementViewTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.staff_user = UserFactory(
            username="staff_user_moto", is_staff=True, is_superuser=False
        )
        cls.superuser = UserFactory(
            username="superuser_moto", is_staff=True, is_superuser=True
        )
        cls.regular_user = UserFactory(
            username="regular_user_moto", is_staff=False, is_superuser=False
        )

        cls.profile_john = ServiceProfileFactory(
            name="John Doe", email="john@example.com"
        )
        cls.profile_jane = ServiceProfileFactory(
            name="Jane Smith", email="jane@example.com"
        )

        cls.moto1 = CustomerMotorcycleFactory(
            brand="Honda",
            model="CBR600RR",
            rego="ABC123",
            vin_number="VIN1234567890ABCDE1",
            engine_number="ENG1",
            service_profile=cls.profile_john,
            created_at=timezone.now() - timezone.timedelta(days=30),
        )
        cls.moto2 = CustomerMotorcycleFactory(
            brand="Yamaha",
            model="YZF-R1",
            rego="DEF456",
            vin_number="VIN1234567890ABCDE2",
            engine_number="ENG2",
            service_profile=cls.profile_jane,
            created_at=timezone.now() - timezone.timedelta(days=20),
        )
        cls.moto3 = CustomerMotorcycleFactory(
            brand="Kawasaki",
            model="Ninja 400",
            rego="GHI789",
            vin_number="VIN1234567890ABCDE3",
            engine_number="ENG3",
            service_profile=cls.profile_john,
            created_at=timezone.now() - timezone.timedelta(days=10),
        )
        cls.moto_no_profile = CustomerMotorcycleFactory(
            brand="Suzuki",
            model="GSX-R750",
            rego="JKL012",
            vin_number="VIN1234567890ABCDE4",
            engine_number="ENG4",
            service_profile=None,
            created_at=timezone.now(),
        )

        cls.list_url = reverse("service:admin_customer_motorcycle_management")

    def setUp(self):
        self.client = Client()

    def test_view_redirects_anonymous_user(self):
        response = self.client.get(self.list_url)
        self.assertRedirects(
            response, reverse("users:login") + f"?next={self.list_url}"
        )

    def test_view_denies_access_to_regular_user(self):
        self.client.login(username="regular_user_moto", password="testpassword")
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 302)

    def test_view_allows_access_to_admin_user(self):
        self.client.login(username="adminuser", password="testpassword")
        self.client.force_login(self.staff_user)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)

    def test_view_grants_access_to_superuser(self):
        self.client.force_login(self.superuser)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)

    def test_get_request_list_all_motorcycles(self):
        self.client.force_login(self.staff_user)
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, "service/admin_customer_motorcycle_management.html"
        )
        self.assertIn("motorcycles", response.context)
        self.assertIn("search_term", response.context)
        self.assertEqual(response.context["search_term"], "")

        motorcycles_in_context = list(response.context["motorcycles"])
        expected_motorcycles = list(
            CustomerMotorcycle.objects.all().order_by("-created_at")
        )
        self.assertListEqual(motorcycles_in_context, expected_motorcycles)
        self.assertEqual(
            len(motorcycles_in_context), CustomerMotorcycle.objects.count()
        )

    def test_get_request_search_by_brand(self):
        self.client.force_login(self.staff_user)
        search_term = "Honda"
        response = self.client.get(f"{self.list_url}?q={search_term}")

        self.assertEqual(response.status_code, 200)
        self.assertIn("motorcycles", response.context)
        self.assertEqual(response.context["search_term"], search_term)

        motorcycles_in_context = list(response.context["motorcycles"])
        self.assertEqual(len(motorcycles_in_context), 1)
        self.assertEqual(motorcycles_in_context[0], self.moto1)

    def test_get_request_search_by_model(self):
        self.client.force_login(self.staff_user)
        search_term = "R1"
        response = self.client.get(f"{self.list_url}?q={search_term}")
        motorcycles_in_context = list(response.context["motorcycles"])
        self.assertEqual(len(motorcycles_in_context), 1)
        self.assertEqual(motorcycles_in_context[0], self.moto2)

    def test_get_request_search_by_rego(self):
        self.client.force_login(self.staff_user)
        search_term = "GHI789"
        response = self.client.get(f"{self.list_url}?q={search_term}")
        motorcycles_in_context = list(response.context["motorcycles"])
        self.assertEqual(len(motorcycles_in_context), 1)
        self.assertEqual(motorcycles_in_context[0], self.moto3)

    def test_get_request_search_by_vin_number(self):
        self.client.force_login(self.staff_user)
        search_term = "ABCDE4"
        response = self.client.get(f"{self.list_url}?q={search_term}")
        motorcycles_in_context = list(response.context["motorcycles"])
        self.assertEqual(len(motorcycles_in_context), 1)
        self.assertEqual(motorcycles_in_context[0], self.moto_no_profile)

    def test_get_request_search_by_engine_number(self):
        self.client.force_login(self.staff_user)
        search_term = "ENG2"
        response = self.client.get(f"{self.list_url}?q={search_term}")
        motorcycles_in_context = list(response.context["motorcycles"])
        self.assertEqual(len(motorcycles_in_context), 1)
        self.assertEqual(motorcycles_in_context[0], self.moto2)

    def test_get_request_search_by_service_profile_name(self):
        self.client.force_login(self.staff_user)
        search_term = "John Doe"
        response = self.client.get(f"{self.list_url}?q={search_term}")
        motorcycles_in_context = list(response.context["motorcycles"])

        self.assertEqual(len(motorcycles_in_context), 2)


    def test_get_request_search_by_service_profile_email(self):
        self.client.force_login(self.staff_user)
        search_term = "jane@example.com"
        response = self.client.get(f"{self.list_url}?q={search_term}")
        motorcycles_in_context = list(response.context["motorcycles"])
        self.assertEqual(len(motorcycles_in_context), 1)
        self.assertEqual(motorcycles_in_context[0], self.moto2)

    def test_get_request_no_search_results(self):
        self.client.force_login(self.staff_user)
        search_term = "NonExistentMotorcycle"
        response = self.client.get(f"{self.list_url}?q={search_term}")

        self.assertEqual(response.status_code, 200)
        self.assertIn("motorcycles", response.context)
        self.assertEqual(len(list(response.context["motorcycles"])), 0)
        self.assertEqual(response.context["search_term"], search_term)

    def test_get_request_pagination(self):

        for i in range(7):
            CustomerMotorcycleFactory(
                created_at=timezone.now() - timezone.timedelta(days=i + 40)
            )

        self.client.force_login(self.staff_user)
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 200)
        self.assertIn("is_paginated", response.context)
        self.assertTrue(response.context["is_paginated"])
        self.assertEqual(len(response.context["motorcycles"]), 10)
        self.assertEqual(
            response.context["paginator"].num_pages,
            (CustomerMotorcycle.objects.count() + 9) // 10,
        )

        response_page2 = self.client.get(f"{self.list_url}?page=2")
        self.assertEqual(response_page2.status_code, 200)
        self.assertIn("motorcycles", response_page2.context)

        self.assertGreater(len(response_page2.context["motorcycles"]), 0)
