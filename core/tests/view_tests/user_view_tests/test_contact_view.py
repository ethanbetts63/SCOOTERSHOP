from django.test import TestCase, Client
from django.urls import reverse
from unittest.mock import patch, MagicMock, call
from core.forms.enquiry_form import EnquiryForm
from dashboard.models import SiteSettings
from django.contrib.messages import get_messages
from core.models import Enquiry


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

        patch_admin_email = patch(
            "django.conf.settings.ADMIN_EMAIL", "admin@example.com"
        )
        self.mock_admin_email = patch_admin_email.start()
        self.addCleanup(patch_admin_email.stop)

        patch_send_email = patch(
            "core.views.user_views.contact_view.send_templated_email"
        )
        self.mock_send_email = patch_send_email.start()
        self.addCleanup(patch_send_email.stop)

    def test_contact_view_get(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        self.assertIn("settings", response.context)
        self.assertEqual(response.context["settings"], self.mock_site_settings)
        self.assertIn("google_api_key", response.context)
        self.assertEqual(response.context["google_api_key"], "test_api_key")
        self.assertIn("form", response.context)
        self.assertIsInstance(response.context["form"], EnquiryForm)

    def test_contact_view_post_valid_form(self):
        form_data = {
            "name": "Test User",
            "email": "test@example.com",
            "message": "Test message",
            "phone_number": "1234567890",
        }
        response = self.client.post(self.url, form_data)

        self.assertEqual(Enquiry.objects.count(), 1)
        enquiry = Enquiry.objects.first()
        self.assertEqual(enquiry.name, "Test User")

        self.assertEqual(self.mock_send_email.call_count, 2)

        customer_call = call(
            recipient_list=[enquiry.email],
            subject="Enquiry Received - Scooter Shop",
            template_name="user_general_enquiry_notification.html",
            context={
                "enquiry": enquiry,
                "SITE_DOMAIN": "127.0.0.1:8000",
                "SITE_SCHEME": "http",
            },
            booking=enquiry,
            profile=enquiry,
        )
        admin_call = call(
            recipient_list=["admin@example.com"],
            subject="New Enquiry - Scooter Shop",
            template_name="admin_general_enquiry_notification.html",
            context={
                "enquiry": enquiry,
                "SITE_DOMAIN": "127.0.0.1:8000",
                "SITE_SCHEME": "http",
            },
            booking=enquiry,
            profile=enquiry,
        )
        self.mock_send_email.assert_has_calls(
            [customer_call, admin_call], any_order=True
        )

        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Your enquiry has been sent successfully!")
        self.assertRedirects(response, self.url)

    def test_contact_view_post_invalid_form(self):
        form_data = {"name": "", "email": "invalid-email", "message": ""}
        response = self.client.post(self.url, form_data)

        self.assertEqual(Enquiry.objects.count(), 0)
        self.mock_send_email.assert_not_called()

        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(
            str(messages[0]),
            "There was an error with your submission. Please correct the errors below.",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/information/contact.html")
        form = response.context["form"]
        self.assertIsInstance(form, EnquiryForm)
        self.assertTrue(form.errors)
