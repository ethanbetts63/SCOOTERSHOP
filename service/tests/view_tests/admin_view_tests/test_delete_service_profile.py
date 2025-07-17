from django.test import TestCase
from django.urls import reverse
from service.models import ServiceProfile
from users.tests.test_helpers.model_factories import staff_factory
from service.tests.test_helpers.model_factories import ServiceProfileFactory
from django.contrib.messages import get_messages


class ServiceProfileDeleteViewTest(TestCase):
    def setUp(self):
        self.admin_user = staff_factory()
        self.client.force_login(self.admin_user)
        self.service_profile = ServiceProfileFactory(name="Test Profile")

    def test_delete_service_profile_post_success(self):
        initial_count = ServiceProfile.objects.count()
        response = self.client.post(
            reverse(
                "service:admin_delete_service_profile",
                kwargs={"pk": self.service_profile.pk},
            )
        )
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("service:admin_service_profiles"))
        self.assertEqual(ServiceProfile.objects.count(), initial_count - 1)
        self.assertFalse(
            ServiceProfile.objects.filter(pk=self.service_profile.pk).exists()
        )
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(
            str(messages[0]), "Service Profile for 'Test Profile' deleted successfully."
        )

    def test_delete_service_profile_post_nonexistent(self):
        initial_count = ServiceProfile.objects.count()
        response = self.client.post(
            reverse("service:admin_delete_service_profile", kwargs={"pk": 999})
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(ServiceProfile.objects.count(), initial_count)

    def test_admin_required_mixin(self):
        self.client.logout()
        response = self.client.post(
            reverse(
                "service:admin_delete_service_profile",
                kwargs={"pk": self.service_profile.pk},
            )
        )
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(
            response,
            reverse("users:login")
            + "?next="
            + reverse(
                "service:admin_delete_service_profile",
                kwargs={"pk": self.service_profile.pk},
            ),
        )
