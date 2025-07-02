from django.test import TestCase, Client
from django.urls import reverse
from ...test_helpers.model_factories import (
    MotorcycleFactory,
    InventorySettingsFactory,
    MotorcycleConditionFactory,
)


class UserMotorcycleDetailsViewTest(TestCase):

    @classmethod
    def setUpTestData(cls):

        cls.client = Client()

        cls.inventory_settings = InventorySettingsFactory()

        cls.condition_used = MotorcycleConditionFactory(
            name="used", display_name="Used"
        )

        cls.motorcycle = MotorcycleFactory(
            brand="TestBrand",
            model="TestModel",
            year=2023,
            price=15000.00,
            conditions=[cls.condition_used.name],
            is_available=True,
        )

        cls.other_motorcycle = MotorcycleFactory(
            brand="OtherBrand",
            model="OtherModel",
            year=2022,
            price=10000.00,
            is_available=True,
        )

    def test_motorcycle_details_view_success(self):

        url = reverse("inventory:motorcycle-detail", kwargs={"pk": self.motorcycle.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

        self.assertTemplateUsed(response, "inventory/user_motorcycle_details.html")

        self.assertIn("motorcycle", response.context)
        self.assertEqual(response.context["motorcycle"], self.motorcycle)

        self.assertIn("inventory_settings", response.context)
        self.assertEqual(
            response.context["inventory_settings"], self.inventory_settings
        )

        self.assertContains(response, self.motorcycle.title)
        self.assertContains(response, str(self.motorcycle.price))
        self.assertContains(response, self.motorcycle.description)

    def test_motorcycle_details_view_404_not_found(self):

        non_existent_pk = self.motorcycle.pk + 999

        url = reverse("inventory:motorcycle-detail", kwargs={"pk": non_existent_pk})

        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_motorcycle_details_view_unavailable_motorcycle(self):

        unavailable_motorcycle = MotorcycleFactory(
            brand="SoldBrand",
            model="SoldModel",
            year=2021,
            price=20000.00,
            is_available=False,
        )
        url = reverse(
            "inventory:motorcycle-detail", kwargs={"pk": unavailable_motorcycle.pk}
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertIn("motorcycle", response.context)
        self.assertEqual(response.context["motorcycle"], unavailable_motorcycle)
        self.assertContains(response, unavailable_motorcycle.title)
