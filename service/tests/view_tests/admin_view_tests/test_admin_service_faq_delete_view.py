from django.test import TestCase
from django.urls import reverse
from service.models import Servicefaq
from users.tests.test_helpers.model_factories import StaffUserFactory
from service.tests.test_helpers.model_factories import ServicefaqFactory
from django.contrib.messages import get_messages


class ServicefaqDeleteViewTest(TestCase):
    def setUp(self):
        self.admin_user = StaffUserFactory()
        self.client.force_login(self.admin_user)
        self.service_faq = ServicefaqFactory(question="Test Service FAQ Question")

    def test_service_faq_delete_get(self):
        response = self.client.get(
            reverse("service:service_faq_delete", kwargs={"pk": self.service_faq.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "service/admin_confirm_delete.html")
        self.assertContains(response, "Confirm Delete faq")
        self.assertContains(response, "Test Service FAQ Question")

    def test_service_faq_delete_post_success(self):
        initial_count = Servicefaq.objects.count()
        response = self.client.post(
            reverse("service:service_faq_delete", kwargs={"pk": self.service_faq.pk})
        )
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("service:service_faq_management"))
        self.assertEqual(Servicefaq.objects.count(), initial_count - 1)
        self.assertFalse(Servicefaq.objects.filter(pk=self.service_faq.pk).exists())
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertIn(
            "The Service faq 'Test Service FAQ Question...' was deleted successfully.",
            str(messages[0]),
        )

    def test_service_faq_delete_post_nonexistent(self):
        initial_count = Servicefaq.objects.count()
        response = self.client.post(
            reverse("service:service_faq_delete", kwargs={"pk": 999})
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(Servicefaq.objects.count(), initial_count)

    def test_admin_required_mixin(self):
        self.client.logout()
        response = self.client.get(
            reverse("service:service_faq_delete", kwargs={"pk": self.service_faq.pk})
        )
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(
            response,
            reverse("users:login")
            + "?next="
            + reverse("service:service_faq_delete", kwargs={"pk": self.service_faq.pk}),
        )
