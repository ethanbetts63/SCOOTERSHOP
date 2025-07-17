from django.test import TestCase
from django.urls import reverse
from inventory.models import SalesTerms
from users.tests.test_helpers.model_factories import UserFactory, StaffUserFactory
from django.contrib.messages import get_messages


class SalesTermsCreateViewTest(TestCase):
    def setUp(self):
        self.admin_user = StaffUserFactory()
        self.client.force_login(self.admin_user)

    def test_create_sales_terms_get(self):
        response = self.client.get(reverse("inventory:terms_and_conditions_create"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "inventory/admin_sales_terms_create.html")
        self.assertContains(response, "Create New Version")
        self.assertIn("form", response.context)

    def test_create_sales_terms_post_success(self):
        initial_count = SalesTerms.objects.count()
        data = {
            "content": "New terms and conditions content.",
        }
        response = self.client.post(
            reverse("inventory:terms_and_conditions_create"), data=data
        )
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(
            response, reverse("inventory:terms_and_conditions_management")
        )
        self.assertEqual(SalesTerms.objects.count(), initial_count + 1)
        new_terms = SalesTerms.objects.latest("created_at")
        self.assertEqual(new_terms.content, "New terms and conditions content.")
        self.assertTrue(new_terms.is_active)
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertIn(
            f"New Terms & Conditions Version {new_terms.version_number} created successfully and set as active.",
            str(messages[0]),
        )

    def test_create_sales_terms_post_invalid(self):
        data = {
            "content": "",
        }
        response = self.client.post(
            reverse("inventory:terms_and_conditions_create"), data=data
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "inventory/admin_sales_terms_create.html")
        self.assertContains(response, "Please correct the errors below.")
        self.assertIn("form", response.context)
        self.assertFalse(response.context["form"].is_valid())

    def test_admin_required_mixin(self):
        self.client.logout()
        response = self.client.get(reverse("inventory:terms_and_conditions_create"))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(
            response,
            reverse("users:login")
            + "?next="
            + reverse("inventory:terms_and_conditions_create"),
        )
