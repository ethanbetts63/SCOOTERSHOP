from django.test import TestCase
from django.urls import reverse
from inventory.tests.test_helpers.model_factories import (
    FeaturedMotorcycleFactory,
    MotorcycleFactory,
    UserFactory,
    StaffUserFactory,
)


class FeaturedMotorcycleManagementViewTest(TestCase):
    def setUp(self):
        self.admin_user = StaffUserFactory()
        self.client.force_login(self.admin_user)

        # Create some motorcycles and featured motorcycles
        self.new_motorcycle1 = MotorcycleFactory(condition="new")
        self.new_motorcycle2 = MotorcycleFactory(condition="new")
        self.used_motorcycle1 = MotorcycleFactory(condition="used")
        self.used_motorcycle2 = MotorcycleFactory(condition="used")

        self.featured_new1 = FeaturedMotorcycleFactory(
            motorcycle=self.new_motorcycle1, category="new", order=1
        )
        self.featured_new2 = FeaturedMotorcycleFactory(
            motorcycle=self.new_motorcycle2, category="new", order=2
        )
        self.featured_used1 = FeaturedMotorcycleFactory(
            motorcycle=self.used_motorcycle1, category="used", order=1
        )
        self.featured_used2 = FeaturedMotorcycleFactory(
            motorcycle=self.used_motorcycle2, category="used", order=2
        )

    def test_featured_motorcycle_management_view_get(self):
        response = self.client.get(reverse("inventory:featured_motorcycles"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, "inventory/admin_featured_motorcycle_management.html"
        )

        # Check if featured_new context contains the correct objects in order
        featured_new_context = list(response.context["featured_new"])
        self.assertEqual(len(featured_new_context), 2)
        self.assertEqual(featured_new_context[0], self.featured_new1)
        self.assertEqual(featured_new_context[1], self.featured_new2)

        # Check if featured_used context contains the correct objects in order
        featured_used_context = list(response.context["featured_used"])
        self.assertEqual(len(featured_used_context), 2)
        self.assertEqual(featured_used_context[0], self.featured_used1)
        self.assertEqual(featured_used_context[1], self.featured_used2)

    def test_admin_required_mixin(self):
        self.client.logout()
        response = self.client.get(reverse("inventory:featured_motorcycles"))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(
            response,
            reverse("users:login")
            + "?next="
            + reverse("inventory:featured_motorcycles"),
        )
