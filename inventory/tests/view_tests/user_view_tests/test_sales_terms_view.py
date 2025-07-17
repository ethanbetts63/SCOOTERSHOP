from django.test import TestCase
from django.urls import reverse
from inventory.models import SalesTerms
from inventory.tests.test_helpers.model_factories import SalesTermsFactory


class SalesTermsViewTest(TestCase):
    def test_sales_terms_view_get_with_active_terms(self):
        active_terms = SalesTermsFactory(is_active=True, content="Active Terms Content")
        # Ensure there are no other active terms
        SalesTerms.objects.exclude(pk=active_terms.pk).update(is_active=False)

        response = self.client.get(reverse("inventory:sales_terms"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "inventory/sales_terms.html")
        self.assertContains(response, "Sales Terms &amp; Conditions")
        self.assertIn("terms", response.context)
        self.assertEqual(response.context["terms"], active_terms)
        self.assertContains(response, "Active Terms Content")

    def test_sales_terms_view_get_no_active_terms(self):
        SalesTerms.objects.all().update(is_active=False)  # Ensure no active terms

        response = self.client.get(reverse("inventory:sales_terms"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "inventory/sales_terms.html")
        self.assertContains(response, "Sales Terms &amp; Conditions")
        self.assertIn("terms", response.context)
        self.assertIsNone(response.context["terms"])

    def test_sales_terms_view_get_multiple_active_terms(self):
        # This scenario should ideally not happen due to model's save method,
        # but testing robustness.
        active_terms1 = SalesTermsFactory(
            is_active=True, content="First Active", version_number=1
        )
        active_terms2 = SalesTermsFactory(
            is_active=True, content="Second Active", version_number=2
        )

        response = self.client.get(reverse("inventory:sales_terms"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "inventory/sales_terms.html")
        self.assertIn("terms", response.context)
        # The view should return the first one it finds, which is usually the one with the lowest PK or created first
        # or the one with the highest version number if ordered by -version_number
        # Given the model's save method, only one should be active. So this test might be redundant.
        # However, if the save method is bypassed, it should still return one.
        self.assertIsNotNone(response.context["terms"])
        # Verify it contains content from one of the active terms
        self.assertTrue(
            "First Active" in response.content.decode()
            or "Second Active" in response.content.decode()
        )
