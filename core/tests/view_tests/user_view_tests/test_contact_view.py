from django.test import TestCase, Client
from django.urls import reverse
from unittest.mock import patch, MagicMock
from core.forms.enquiry_form import EnquiryForm
from dashboard.models import SiteSettings
from django.contrib.messages import get_messages


class ContactViewTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.url = reverse("core:contact")
        self.template_name = "core/information/contact.html"

        self.mock_site_settings = MagicMock(spec=SiteSettings)
        self.mock_site_settings.google_places_place_id = "test_place_id"
        self.mock_site_settings.google_api_key = "test_api_key"

        patch_google_api_key = patch(
            "django.conf.settings.GOOGLE_API_KEY", "test_api_key"
        )
        self.mock_google_api_key = patch_google_api_key.start()
        self.addCleanup(patch_google_api_key.stop)

        patch_site_settings = patch(
            "dashboard.models.SiteSettings.get_settings",
            return_value=self.mock_site_settings,
        )
        self.mock_get_settings = patch_site_settings.start()
        self.addCleanup(patch_site_settings.stop)

        self.mock_enquiry_form_instance = MagicMock(spec=EnquiryForm)
        patch_enquiry_form = patch(
            "core.views.user_views.contact_view.EnquiryForm",
            return_value=self.mock_enquiry_form_instance,
        )
        self.mock_enquiry_form_class = patch_enquiry_form.start()
        self.addCleanup(patch_enquiry_form.stop)

        patch_admin_email = patch(
            "django.conf.settings.ADMIN_EMAIL", "admin@example.com"
        )
        self.mock_admin_email = patch_admin_email.start()
        self.addCleanup(patch_admin_email.stop)

    def test_contact_view_get(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        self.assertIn("settings", response.context)
        self.assertEqual(response.context["settings"], self.mock_site_settings)
        self.assertIn("google_api_key", response.context)
        self.assertEqual(response.context["google_api_key"], "test_api_key")
        self.assertIn("form", response.context)
        self.assertEqual(response.context["form"], self.mock_enquiry_form_instance)

    def test_contact_view_post_valid_form(self):
        self.mock_enquiry_form_instance.is_valid.return_value = True
        mock_enquiry_instance = MagicMock()
        mock_enquiry_instance.name = "Test User"
        mock_enquiry_instance.email = "test@example.com"
        mock_enquiry_instance.message = "Test message"
        mock_enquiry_instance.phone_number = "1234567890"
        self.mock_enquiry_form_instance.save.return_value = mock_enquiry_instance

        response = self.client.post(
            self.url,
            {
                "name": "Test User",
                "email": "test@example.com",
                "message": "Test message",
                "phone_number": "1234567890",
            },
        )

        self.mock_enquiry_form_class.assert_called_once()
        self.mock_enquiry_form_instance.is_valid.assert_called_once()
        self.mock_enquiry_form_instance.save.assert_called_once()

        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Your enquiry has been sent successfully!")
        self.assertRedirects(response, self.url)

    def test_contact_view_post_invalid_form(self):
        self.mock_enquiry_form_instance.is_valid.return_value = False

        response = self.client.post(
            self.url, {"name": "", "email": "invalid-email", "message": ""}
        )

        self.assertEqual(self.mock_enquiry_form_class.call_count, 2)
        self.mock_enquiry_form_instance.is_valid.assert_called_once()
        self.mock_enquiry_form_instance.save.assert_not_called()

        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(
            str(messages[0]),
            "There was an error with your submission. Please correct the errors below.",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/information/contact.html")
        self.assertEqual(response.context["form"], self.mock_enquiry_form_instance)
