from django.test import TestCase
from django.urls import reverse
from inventory.tests.test_helpers.model_factories import SalesTermsFactory, UserFactory


class SalesTermsDetailsViewTest(TestCase):
    def setUp(self):
        self.admin_user = UserFactory(is_staff=True)
        self.client.force_login(self.admin_user)
        self.sales_terms = SalesTermsFactory(version_number=1, content="Test Content")

    def test_sales_terms_details_view_get(self):
        response = self.client.get(
            reverse(
                "inventory:terms_and_conditions_detail",
                kwargs={"pk": self.sales_terms.pk},
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "inventory/admin_sales_terms_details.html")
        self.assertContains(
            response, f"View T&amp;C Version {self.sales_terms.version_number}"
        )
        self.assertIn("terms_version", response.context)
        self.assertEqual(response.context["terms_version"], self.sales_terms)

    def test_sales_terms_details_view_nonexistent(self):
        response = self.client.get(
            reverse("inventory:terms_and_conditions_detail", kwargs={"pk": 999})
        )
        self.assertEqual(response.status_code, 404)

    def test_admin_required_mixin(self):
        self.client.logout()
        response = self.client.get(
            reverse(
                "inventory:terms_and_conditions_detail",
                kwargs={"pk": self.sales_terms.pk},
            )
        )
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(
            response,
            reverse("users:login")
            + "?next="
            + reverse(
                "inventory:terms_and_conditions_detail",
                kwargs={"pk": self.sales_terms.pk},
            ),
        )
