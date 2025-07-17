from django.test import TestCase, override_settings
from django.urls import reverse
from dashboard.models import GoogleMyBusinessAccount
from django.contrib.auth import get_user_model

User = get_user_model()


@override_settings(
    SITE_BASE_URL="http://testserver",
)
class GoogleMyBusinessSettingsViewTest(TestCase):
    def setUp(self):
        GoogleMyBusinessAccount.objects.all().delete()
        self.client = self.client_class()
        self.admin_user = User.objects.create_user(
            username="admin",
            email="admin@example.com",
            password="password",
            is_staff=True,
            is_superuser=True,
        )
        self.user = User.objects.create_user(
            username="user",
            email="user@example.com",
            password="password",
            is_staff=False,
            is_superuser=False,
        )

    def test_authenticated_admin_access(self):
        self.client.login(username="admin", password="password")
        response = self.client.get(reverse("dashboard:gmb_settings"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "dashboard/admin_gmb_settings.html")
        self.assertIn("page_title", response.context)
        self.assertEqual(response.context["page_title"], "GMB Integration Settings")
        self.assertIn("gmb_account", response.context)
        self.assertIsInstance(response.context["gmb_account"], GoogleMyBusinessAccount)

    def test_unauthenticated_access_redirects_to_login(self):
        response = self.client.get(reverse("dashboard:gmb_settings"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("users:login"), response.url)

    def test_non_admin_access_redirects_to_login(self):
        self.client.login(username="user", password="password")
        response = self.client.get(reverse("dashboard:gmb_settings"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("users:login"), response.url)
