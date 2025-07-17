from django.test import TestCase
from django.urls import reverse
from service.tests.test_helpers.model_factories import ServiceTypeFactory, UserFactory
from django.contrib.messages import get_messages
import json


class ToggleServiceTypeActiveStatusTest(TestCase):
    def setUp(self):
        self.admin_user = UserFactory(is_staff=True)
        self.non_staff_user = UserFactory(is_staff=False)
        self.service_type = ServiceTypeFactory(name="Test Service", is_active=True)

    def test_toggle_status_post_success_deactivate(self):
        self.client.force_login(self.admin_user)
        response = self.client.post(
            reverse(
                "service:toggle_service_type_active_status",
                kwargs={"pk": self.service_type.pk},
            )
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["status"], "success")
        self.assertFalse(data["is_active"])
        self.assertIn(
            "Service type 'Test Service' has been deactivated.", data["message"]
        )
        self.service_type.refresh_from_db()
        self.assertFalse(self.service_type.is_active)
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(
            str(messages[0]), "Service type 'Test Service' has been deactivated."
        )

    def test_toggle_status_post_success_activate(self):
        self.service_type.is_active = False
        self.service_type.save()
        self.client.force_login(self.admin_user)
        response = self.client.post(
            reverse(
                "service:toggle_service_type_active_status",
                kwargs={"pk": self.service_type.pk},
            )
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["status"], "success")
        self.assertTrue(data["is_active"])
        self.assertIn(
            "Service type 'Test Service' has been activated.", data["message"]
        )
        self.service_type.refresh_from_db()
        self.assertTrue(self.service_type.is_active)
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(
            str(messages[0]), "Service type 'Test Service' has been activated."
        )

    def test_toggle_status_post_nonexistent_service_type(self):
        self.client.force_login(self.admin_user)
        response = self.client.post(
            reverse("service:toggle_service_type_active_status", kwargs={"pk": 999})
        )
        self.assertEqual(response.status_code, 404)

    def test_toggle_status_get_method_not_allowed(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(
            reverse(
                "service:toggle_service_type_active_status",
                kwargs={"pk": self.service_type.pk},
            )
        )
        self.assertEqual(response.status_code, 405)
        data = json.loads(response.content)
        self.assertEqual(data["error"], "Invalid request method")

    def test_toggle_status_non_staff_user(self):
        self.client.force_login(self.non_staff_user)
        response = self.client.post(
            reverse(
                "service:toggle_service_type_active_status",
                kwargs={"pk": self.service_type.pk},
            )
        )
        self.assertEqual(response.status_code, 302)  # Redirect to login
        self.assertRedirects(
            response,
            reverse("users:login")
            + "?next="
            + reverse(
                "service:toggle_service_type_active_status",
                kwargs={"pk": self.service_type.pk},
            ),
        )

    def test_toggle_status_unauthenticated_user(self):
        self.client.logout()
        response = self.client.post(
            reverse(
                "service:toggle_service_type_active_status",
                kwargs={"pk": self.service_type.pk},
            )
        )
        self.assertEqual(response.status_code, 302)  # Redirect to login
        self.assertRedirects(
            response,
            reverse("users:login")
            + "?next="
            + reverse(
                "service:toggle_service_type_active_status",
                kwargs={"pk": self.service_type.pk},
            ),
        )
