from django.test import TestCase, Client
from django.urls import reverse
from unittest.mock import patch, MagicMock
from dashboard.tests.test_helpers.model_factories import SiteSettingsFactory
from users.tests.test_helpers.model_factories import UserFactory, StaffUserFactory


class PrivacyPolicyViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse("core:privacy")
        self.index_url = reverse("core:index")
        self.template_name = "core/information/privacy.html"

        self.staff_user = StaffUserFactory()
        self.client.force_login(self.staff_user)

        self.site_settings = SiteSettingsFactory()
        patch_site_settings = patch(
            "dashboard.models.SiteSettings.get_settings",
            return_value=self.site_settings,
        )
        self.mock_get_settings = patch_site_settings.start()
        self.addCleanup(patch_site_settings.stop)

    def test_privacy_policy_view_displayed_when_enabled(self):
        self.site_settings.enable_privacy_policy_page = True
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        self.assertIn("settings", response.context)
        self.assertEqual(response.context["settings"], self.site_settings)

    def test_privacy_policy_view_accessible_for_staff_when_disabled(self):
        self.site_settings.enable_privacy_policy_page = False
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
