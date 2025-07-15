from django.test import TestCase, Client
from django.urls import reverse
from decimal import Decimal
import datetime
from inventory.models import Motorcycle
from ...test_helpers.model_factories import (
    MotorcycleFactory,
    MotorcycleConditionFactory,
)


class MotorcycleListViewTest(TestCase):

    @classmethod
    def setUpTestData(cls):

        cls.client = Client()

        cls.condition_new = MotorcycleConditionFactory(name="new", display_name="New")
        cls.condition_used = MotorcycleConditionFactory(
            name="used", display_name="Used"
        )
        cls.condition_demo = MotorcycleConditionFactory(
            name="demo", display_name="Demo"
        )

    def setUp(self):
        Motorcycle.objects.all().delete()

    def test_new_motorcycles_page_renders_empty_initially(self):
        response = self.client.get(reverse("inventory:new"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "inventory/motorcycle_list.html")

        self.assertIn("motorcycles", response.context)
        self.assertIn("page_obj", response.context)
        self.assertIn("unique_makes", response.context)
        self.assertIn("current_condition_slug", response.context)
        self.assertIn("page_title", response.context)
        self.assertIn("years", response.context)

        page_obj = response.context["page_obj"]
        self.assertEqual(len(response.context["motorcycles"]), 0)
        self.assertFalse(page_obj.object_list)

        expected_new_makes = set(
            Motorcycle.objects.filter(conditions__name="new")
            .values_list("brand", flat=True)
            .distinct()
        )
        self.assertEqual(set(response.context["unique_makes"]), expected_new_makes)

        self.assertEqual(response.context["current_condition_slug"], "new")
        self.assertEqual(response.context["page_title"], "New Motorcycles")
        self.assertIsInstance(response.context["years"], list)
        self.assertGreater(len(response.context["years"]), 0)
        self.assertContains(response, "No motorcycles match the current criteria.")

    def test_used_motorcycles_page_renders_empty_initially(self):

        response = self.client.get(reverse("inventory:used"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "inventory/motorcycle_list.html")

        page_obj = response.context["page_obj"]
        self.assertEqual(len(response.context["motorcycles"]), 0)
        self.assertFalse(page_obj.object_list)

        expected_used_makes = set(
            Motorcycle.objects.filter(conditions__name__in=["used", "demo"])
            .values_list("brand", flat=True)
            .distinct()
        )
        self.assertEqual(set(response.context["unique_makes"]), expected_used_makes)

        self.assertEqual(response.context["current_condition_slug"], "used")
        self.assertEqual(response.context["page_title"], "Used Motorcycles")
        self.assertContains(response, "No motorcycles match the current criteria.")

    def test_no_motorcycles_found_display_initial_load(self):
        response = self.client.get(reverse("inventory:all"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "inventory/motorcycle_list.html")

        self.assertIn("motorcycles", response.context)
        self.assertIn("page_obj", response.context)
        self.assertIn("unique_makes", response.context)
        self.assertIn("current_condition_slug", response.context)
        self.assertIn("page_title", response.context)
        self.assertIn("years", response.context)

        page_obj = response.context["page_obj"]
        self.assertEqual(len(response.context["motorcycles"]), 0)
        self.assertFalse(page_obj.object_list)

        expected_all_makes = set(
            Motorcycle.objects.values_list("brand", flat=True).distinct()
        )
        self.assertEqual(set(response.context["unique_makes"]), expected_all_makes)

        self.assertEqual(response.context["current_condition_slug"], "all")
        self.assertEqual(response.context["page_title"], "All Motorcycles")
        self.assertIsInstance(response.context["years"], list)
        self.assertGreater(len(response.context["years"]), 0)
        self.assertContains(response, "No motorcycles match the current criteria.")
