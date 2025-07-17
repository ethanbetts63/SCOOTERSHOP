from django.test import TestCase, Client
from django.urls import reverse
from unittest.mock import patch, MagicMock
from dashboard.models import SiteSettings
from users.tests.test_helpers.model_factories import UserFactory


class SecurityPolicyViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse("core:security")
        self.template_name = "core/information/security.html"

        self.staff_user = UserFactory(is_staff=True)
        self.client.force_login(self.staff_user)

        self.mock_site_settings = MagicMock(spec=SiteSettings)
        patch_site_settings = patch(
            "dashboard.models.SiteSettings.get_settings",
            return_value=self.mock_site_settings,
        )
        self.mock_get_settings = patch_site_settings.start()
        self.addCleanup(patch_site_settings.stop)

    def test_security_policy_view_displayed_when_enabled(self):
        self.mock_site_settings.enable_security_page = True
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        self.assertIn("settings", response.context)
        self.assertEqual(response.context["settings"], self.mock_site_settings)

    def test_security_policy_view_accessible_for_staff_when_disabled(self):
        self.mock_site_settings.enable_security_page = False
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
