from django.test import TestCase
from django.urls import reverse
from unittest.mock import patch, MagicMock
from users.tests.test_helpers.model_factories import StaffUserFactory
from inventory.tests.test_helpers.model_factories import MotorcycleFactory, FeaturedMotorcycleFactory
from django.contrib.messages import get_messages

class FeaturedMotorcycleCreateUpdateViewTest(TestCase):
    def setUp(self):
        self.admin_user = StaffUserFactory()
        self.client.force_login(self.admin_user)
        self.motorcycle = MotorcycleFactory()
        self.featured_motorcycle = FeaturedMotorcycleFactory(
            motorcycle=self.motorcycle, category="new", order=1
        )

    def test_create_featured_motorcycle_get(self):
        response = self.client.get(
            reverse("inventory:add_featured_motorcycle") + "?category=new"
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, "inventory/admin_featured_motorcycle_create_update.html"
        )
        self.assertContains(response, "Add New Featured New Motorcycle")
        self.assertIn("form", response.context)
        self.assertEqual(response.context["motorcycle_condition"], "new")

    def test_update_featured_motorcycle_get(self):
        response = self.client.get(
            reverse(
                "inventory:update_featured_motorcycle",
                kwargs={"pk": self.featured_motorcycle.pk},
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, "inventory/admin_featured_motorcycle_create_update.html"
        )
        self.assertContains(
            response,
            f"Edit Featured {self.featured_motorcycle.category.title()} Motorcycle",
        )
        self.assertIn("form", response.context)
        self.assertEqual(
            response.context["featured_motorcycle"], self.featured_motorcycle
        )
        self.assertEqual(response.context["selected_motorcycle"], self.motorcycle)

    @patch(
        "inventory.forms.admin_featured_motorcycle_form.FeaturedMotorcycleForm.is_valid",
        MagicMock(return_value=True),
    )
    @patch(
        "inventory.forms.admin_featured_motorcycle_form.FeaturedMotorcycleForm.save",
        MagicMock(
            side_effect=lambda: FeaturedMotorcycleFactory(
                motorcycle=MotorcycleFactory()
            )
        ),
    )
    def test_create_featured_motorcycle_post_success(self):
        response = self.client.post(
            reverse("inventory:add_featured_motorcycle") + "?category=new",
            data={"motorcycle": self.motorcycle.pk, "category": "new", "order": 2},
        )
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("inventory:featured_motorcycles"))
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Featured motorcycle saved successfully!")

    @patch(
        "inventory.forms.admin_featured_motorcycle_form.FeaturedMotorcycleForm.is_valid",
        MagicMock(return_value=False),
    )
    def test_create_featured_motorcycle_post_invalid(self):
        response = self.client.post(
            reverse("inventory:add_featured_motorcycle") + "?category=new", data={}
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, "inventory/admin_featured_motorcycle_create_update.html"
        )
        self.assertContains(response, "Please correct the errors below.")
        self.assertIn("form", response.context)

    @patch(
        "inventory.forms.admin_featured_motorcycle_form.FeaturedMotorcycleForm.is_valid",
        MagicMock(return_value=True),
    )
    @patch(
        "inventory.forms.admin_featured_motorcycle_form.FeaturedMotorcycleForm.save",
        MagicMock(
            side_effect=lambda: FeaturedMotorcycleFactory(
                motorcycle=MotorcycleFactory()
            )
        ),
    )
    def test_update_featured_motorcycle_post_success(self):
        response = self.client.post(
            reverse(
                "inventory:update_featured_motorcycle",
                kwargs={"pk": self.featured_motorcycle.pk},
            ),
            data={"motorcycle": self.motorcycle.pk, "category": "new", "order": 5},
        )
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("inventory:featured_motorcycles"))
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Featured motorcycle saved successfully!")

    @patch(
        "inventory.forms.admin_featured_motorcycle_form.FeaturedMotorcycleForm.is_valid",
        MagicMock(return_value=False),
    )
    def test_update_featured_motorcycle_post_invalid(self):
        response = self.client.post(
            reverse(
                "inventory:update_featured_motorcycle",
                kwargs={"pk": self.featured_motorcycle.pk},
            ),
            data={},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, "inventory/admin_featured_motorcycle_create_update.html"
        )
        self.assertContains(response, "Please correct the errors below.")
        self.assertIn("form", response.context)

    def test_get_object_nonexistent(self):
        response = self.client.get(
            reverse("inventory:update_featured_motorcycle", kwargs={"pk": 999})
        )
        self.assertEqual(response.status_code, 404)

    def test_admin_required_mixin(self):
        self.client.logout()
        response = self.client.get(
            reverse("inventory:add_featured_motorcycle") + "?category=new"
        )
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(
            response,
            reverse("users:login")
            + "?next="
            + reverse("inventory:add_featured_motorcycle")
            + "%3Fcategory%3Dnew",
        )
