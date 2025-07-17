from django.test import TestCase
from django.urls import reverse
from service.models import ServiceTerms
from users.tests.test_helpers.model_factories import staff_factory
from django.contrib.messages import get_messages


class ServiceTermsCreateViewTest(TestCase):
    def setUp(self):
        self.admin_user = staff_factory()
        self.client.force_login(self.admin_user)

    def test_create_service_terms_get(self):
        response = self.client.get(reverse("service:service_terms_create"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "service/admin_service_terms_create.html")
        self.assertContains(response, "Create New Service Terms Version")
        self.assertIn("form", response.context)

    def test_create_service_terms_post_success(self):
        initial_count = ServiceTerms.objects.count()
        data = {
            "content": "New service terms and conditions content.",
        }
        response = self.client.post(reverse("service:service_terms_create"), data=data)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("service:service_terms_management"))
        self.assertEqual(ServiceTerms.objects.count(), initial_count + 1)
        new_terms = ServiceTerms.objects.latest("created_at")
        self.assertEqual(new_terms.content, "New service terms and conditions content.")
        self.assertTrue(new_terms.is_active)
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertIn(
            f"New Service Terms Version {new_terms.version_number} created successfully and set as active.",
            str(messages[0]),
        )

    def test_create_service_terms_post_invalid(self):
        data = {
            "content": "",
        }
        response = self.client.post(reverse("service:service_terms_create"), data=data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "service/admin_service_terms_create.html")
        self.assertContains(response, "Please correct the errors below.")
        self.assertIn("form", response.context)
        self.assertFalse(response.context["form"].is_valid())

    def test_admin_required_mixin(self):
        self.client.logout()
        response = self.client.get(reverse("service:service_terms_create"))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(
            response,
            reverse("users:login") + "?next=" + reverse("service:service_terms_create"),
        )
