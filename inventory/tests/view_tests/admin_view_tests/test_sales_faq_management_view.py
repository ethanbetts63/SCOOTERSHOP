from django.test import TestCase
from django.urls import reverse
from inventory.models import Salesfaq
from inventory.tests.test_helpers.model_factories import SalesfaqFactory
from users.tests.test_helpers.model_factories import UserFactory, StaffUserFactory


class SalesfaqManagementViewTest(TestCase):
    def setUp(self):
        self.admin_user = StaffUserFactory()
        self.client.force_login(self.admin_user)

        # Create some FAQs for testing pagination and ordering
        for i in range(20):
            SalesfaqFactory(display_order=i, booking_step="general")
        self.faq_step1 = SalesfaqFactory(booking_step="step1", display_order=0)

    def test_sales_faq_management_view_get(self):
        response = self.client.get(reverse("inventory:sales_faq_management"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "inventory/admin_sales_faq_management.html")
        self.assertContains(response, "Sales faqs Management")
        self.assertIn("sales_faqs", response.context)
        self.assertEqual(len(response.context["sales_faqs"]), 15)  # Paginate by 15

    def test_sales_faq_management_view_pagination(self):
        response = self.client.get(
            reverse("inventory:sales_faq_management") + "?page=2"
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "inventory/admin_sales_faq_management.html")
        self.assertIn("sales_faqs", response.context)
        self.assertEqual(
            len(response.context["sales_faqs"]), 6
        )  # 20 general + 1 step1 = 21 total. 21 - 15 = 6 on second page

    def test_sales_faq_management_view_ordering(self):
        response = self.client.get(reverse("inventory:sales_faq_management"))
        sales_faqs = list(response.context["sales_faqs"])

        # The ordering is by -booking_step, then display_order
        # 'general' comes after 'step1' alphabetically, so -'general' comes before -'step1'
        # Therefore, general FAQs will appear before step1 FAQs.
        # Check the first few elements to ensure general FAQs are first and ordered by display_order
        self.assertEqual(sales_faqs[0].booking_step, "general")
        self.assertEqual(sales_faqs[0].display_order, 0)
        self.assertEqual(sales_faqs[1].booking_step, "general")
        self.assertEqual(sales_faqs[1].display_order, 1)

        # Check that the faq_step1 is present in the queryset
        self.assertIn(self.faq_step1, Salesfaq.objects.all())

    def test_admin_required_mixin(self):
        self.client.logout()
        response = self.client.get(reverse("inventory:sales_faq_management"))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(
            response,
            reverse("users:login")
            + "?next="
            + reverse("inventory:sales_faq_management"),
        )
