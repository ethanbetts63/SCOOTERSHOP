from django.test import TestCase
from django.urls import reverse
from inventory.tests.test_helpers.model_factories import (
    SalesTermsFactory,
    SalesBookingFactory,
)
from users.tests.test_helpers.model_factories import UserFactory, StaffUserFactory

class SalesTermsManagementViewTest(TestCase):
    def setUp(self):
        self.admin_user = StaffUserFactory()
        self.client.force_login(self.admin_user)
        self.terms_v1 = SalesTermsFactory(version_number=1, is_active=False)
        self.terms_v2 = SalesTermsFactory(version_number=2, is_active=True)
        self.terms_v3 = SalesTermsFactory(version_number=3, is_active=False)
        SalesBookingFactory(sales_terms_version=self.terms_v2)

    def test_sales_terms_management_view_get(self):
        response = self.client.get(reverse("inventory:terms_and_conditions_management"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "inventory/admin_sales_terms_management.html")
        self.assertContains(response, "Sales Terms &amp; Conditions Management")
        self.assertIn("terms_versions", response.context)
        terms_versions = list(response.context["terms_versions"])
        self.assertEqual(terms_versions[0], self.terms_v3)
        self.assertEqual(terms_versions[1], self.terms_v2)
        self.assertEqual(terms_versions[2], self.terms_v1)
        self.assertEqual(terms_versions[1].booking_count, 1)  # terms_v2 has 1 booking
        self.assertEqual(terms_versions[0].booking_count, 0)  # terms_v3 has 0 bookings

    def test_sales_terms_management_view_pagination(self):
        for i in range(4, 15):
            SalesTermsFactory(version_number=i)

        response = self.client.get(
            reverse("inventory:terms_and_conditions_management") + "?page=2"
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "inventory/admin_sales_terms_management.html")
        self.assertIn("terms_versions", response.context)
        self.assertEqual(
            len(response.context["terms_versions"]), 4
        )  

    def test_admin_required_mixin(self):
        self.client.logout()
        response = self.client.get(reverse("inventory:terms_and_conditions_management"))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(
            response,
            reverse("users:login")
            + "?next="
            + reverse("inventory:terms_and_conditions_management"),
        )
