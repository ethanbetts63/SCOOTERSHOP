from django.test import TestCase, Client
from django.urls import reverse
from unittest.mock import patch, MagicMock
from dashboard.models import SiteSettings
from users.tests.test_helpers.model_factories import UserFactory, StaffUserFactory


class TermsOfUseViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse("core:terms")
        self.template_name = "core/information/terms.html"

        self.staff_user = StaffUserFactory()
        self.client.force_login(self.staff_user)

        self.mock_site_settings = MagicMock(spec=SiteSettings)
        patch_site_settings = patch(
            "dashboard.models.SiteSettings.get_settings",
            return_value=self.mock_site_settings,
        )
        self.mock_get_settings = patch_site_settings.start()
        self.addCleanup(patch_site_settings.stop)
