from django.test import TestCase
from django.urls import reverse
from inventory.models import Salesfaq
from inventory.tests.test_helpers.model_factories import SalesfaqFactory, UserFactory
from django.contrib.messages import get_messages


class SalesfaqCreateUpdateViewTest(TestCase):
    def setUp(self):
        self.admin_user = UserFactory(is_staff=True)
        self.client.force_login(self.admin_user)

    def test_create_sales_faq_get(self):
        response = self.client.get(reverse("inventory:sales_faq_create"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, "inventory/admin_sales_faq_create_update.html"
        )
        self.assertContains(response, "Create Sales faq")
        self.assertIn("form", response.context)
        self.assertFalse(response.context["is_edit_mode"])

    def test_update_sales_faq_get(self):
        faq = SalesfaqFactory()
        response = self.client.get(
            reverse("inventory:sales_faq_update", kwargs={"pk": faq.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, "inventory/admin_sales_faq_create_update.html"
        )
        self.assertContains(response, "Edit Sales faq")
        self.assertIn("form", response.context)
        self.assertTrue(response.context["is_edit_mode"])
        self.assertEqual(response.context["form"].instance, faq)

    def test_create_sales_faq_post_success(self):
        data = {
            "booking_step": "general",
            "question": "New Test Question",
            "answer": "New Test Answer",
            "display_order": 1,
            "is_active": True,
        }
        response = self.client.post(reverse("inventory:sales_faq_create"), data=data)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("inventory:sales_faq_management"))
        self.assertTrue(Salesfaq.objects.filter(question="New Test Question").exists())
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertIn("created successfully", str(messages[0]))

    def test_create_sales_faq_post_invalid(self):
        data = {
            "booking_step": "general",
            "question": "",
            "answer": "New Test Answer",
            "display_order": 1,
            "is_active": True,
        }
        response = self.client.post(reverse("inventory:sales_faq_create"), data=data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, "inventory/admin_sales_faq_create_update.html"
        )
        self.assertContains(response, "Please correct the errors below.")
        self.assertIn("form", response.context)
        self.assertFalse(response.context["form"].is_valid())

    def test_update_sales_faq_post_success(self):
        faq = SalesfaqFactory(question="Original Question")
        data = {
            "booking_step": faq.booking_step,
            "question": "Updated Question",
            "answer": faq.answer,
            "display_order": faq.display_order,
            "is_active": faq.is_active,
        }
        response = self.client.post(
            reverse("inventory:sales_faq_update", kwargs={"pk": faq.pk}), data=data
        )
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("inventory:sales_faq_management"))
        faq.refresh_from_db()
        self.assertEqual(faq.question, "Updated Question")
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertIn("updated successfully", str(messages[0]))

    def test_update_sales_faq_post_invalid(self):
        faq = SalesfaqFactory(question="Original Question")
        data = {
            "booking_step": faq.booking_step,
            "question": "",
            "answer": faq.answer,
            "display_order": faq.display_order,
            "is_active": faq.is_active,
        }
        response = self.client.post(
            reverse("inventory:sales_faq_update", kwargs={"pk": faq.pk}), data=data
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, "inventory/admin_sales_faq_create_update.html"
        )
        self.assertContains(response, "Please correct the errors below.")
        self.assertIn("form", response.context)
        self.assertFalse(response.context["form"].is_valid())

    def test_admin_required_mixin(self):
        self.client.logout()
        response = self.client.get(reverse("inventory:sales_faq_create"))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(
            response,
            reverse("users:login") + "?next=" + reverse("inventory:sales_faq_create"),
        )
