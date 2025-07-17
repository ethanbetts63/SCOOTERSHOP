from django.test import TestCase
from django.urls import reverse
from service.tests.test_helpers.model_factories import ServicefaqFactory
from users.tests.test_helpers.model_factories import StaffUserFactory


class ServicefaqManagementViewTest(TestCase):
    def setUp(self):
        self.admin_user = StaffUserFactory()
        self.client.force_login(self.admin_user)

        # Create some FAQs for testing pagination and ordering
        for i in range(20):
            ServicefaqFactory(display_order=i, booking_step="general")
        self.faq_step1 = ServicefaqFactory(booking_step="step1", display_order=0)

    def test_service_faq_management_view_get(self):
        response = self.client.get(reverse("service:service_faq_management"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "service/admin_service_faq_management.html")
        self.assertContains(response, "Service faqs Management")
        self.assertIn("service_faqs", response.context)
        self.assertEqual(len(response.context["service_faqs"]), 15)  # Paginate by 15

    def test_service_faq_management_view_pagination(self):
        response = self.client.get(
            reverse("service:service_faq_management") + "?page=2"
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "service/admin_service_faq_management.html")
        self.assertIn("service_faqs", response.context)
        self.assertEqual(
            len(response.context["service_faqs"]), 6
        )  # 20 general + 1 step1 = 21 total. 21 - 15 = 6 on second page

    def test_service_faq_management_view_ordering(self):
        response = self.client.get(reverse("service:service_faq_management"))
        service_faqs = list(response.context["service_faqs"])

        # The ordering is by booking_step, then display_order
        # 'general' comes after 'step1' alphabetically.
        # So, 'step1' FAQs come before 'general' FAQs.
        # Within 'general', they are ordered by display_order, then question.
        

    def test_admin_required_mixin(self):
        self.client.logout()
        response = self.client.get(reverse("service:service_faq_management"))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(
            response,
            reverse("users:login")
            + "?next="
            + reverse("service:service_faq_management"),
        )
