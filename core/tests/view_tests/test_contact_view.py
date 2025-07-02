from django.test import TestCase
from django.urls import reverse
from unittest.mock import patch, MagicMock
from django.contrib.messages import get_messages

from core.forms.enquiry_form import EnquiryForm
from dashboard.models import SiteSettings, AboutPageContent

class ContactViewTest(TestCase):
    """
    Tests for the core app's ContactView.
    """

    def setUp(self):
        self.url = reverse('core:contact')
        self.mock_site_settings = MagicMock(spec=SiteSettings)
        self.mock_site_settings.enable_about_page = True
        self.mock_site_settings.google_api_key = 'TEST_API_KEY'

        self.mock_about_content = MagicMock(spec=AboutPageContent)
        self.mock_about_content.pk = 1

    @patch('dashboard.models.SiteSettings.get_settings')
    @patch('dashboard.models.AboutPageContent.objects.get')
    def test_contact_view_GET_success(self, mock_get_about_content, mock_get_site_settings):
        """
        Test that the contact view renders successfully with all context data.
        """
        mock_get_site_settings.return_value = self.mock_site_settings
        mock_get_about_content.return_value = self.mock_about_content

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/information/contact.html')
        self.assertIsInstance(response.context['form'], EnquiryForm)
        self.assertEqual(response.context['settings'], self.mock_site_settings)
        self.assertEqual(response.context['about_content'], self.mock_about_content)
        self.assertEqual(response.context['google_api_key'], 'TEST_API_KEY')

    @patch('dashboard.models.SiteSettings.get_settings')
    @patch('dashboard.models.AboutPageContent.objects.get')
    def test_contact_view_GET_no_about_content(self, mock_get_about_content, mock_get_site_settings):
        """
        Test that the contact view renders successfully when AboutPageContent does not exist.
        """
        mock_get_site_settings.return_value = self.mock_site_settings
        mock_get_about_content.side_effect = AboutPageContent.DoesNotExist

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/information/contact.html')
        self.assertIsNone(response.context['about_content'])

    @patch('core.forms.enquiry_form.EnquiryForm')
    @patch('django.core.mail.send_mail')
    @patch('dashboard.models.SiteSettings.get_settings')
    @patch('dashboard.models.AboutPageContent.objects.get')
    def test_contact_view_POST_valid_form(self, mock_get_about_content, mock_get_site_settings, mock_send_mail, mock_enquiry_form):
        """
        Test valid form submission for ContactView.
        """
        mock_get_site_settings.return_value = self.mock_site_settings
        mock_get_about_content.return_value = self.mock_about_content

        mock_form_instance = mock_enquiry_form.return_value
        mock_form_instance.is_valid.return_value = True
        mock_form_instance.save.return_value = MagicMock(name='enquiry_mock', email='test@example.com', name_field='Test User', message='Hello', phone_number='1234567890')

        response = self.client.post(self.url, data={'name': 'Test User', 'email': 'test@example.com', 'message': 'Hello'})

        mock_form_instance.is_valid.assert_called_once()
        mock_form_instance.save.assert_called_once()
        self.assertEqual(mock_send_mail.call_count, 2) # One for user, one for admin
        self.assertRedirects(response, self.url)

        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), 'Your enquiry has been sent successfully!')

    @patch('core.forms.enquiry_form.EnquiryForm')
    @patch('django.core.mail.send_mail')
    @patch('dashboard.models.SiteSettings.get_settings')
    @patch('dashboard.models.AboutPageContent.objects.get')
    def test_contact_view_POST_invalid_form(self, mock_get_about_content, mock_get_site_settings, mock_send_mail, mock_enquiry_form):
        """
        Test invalid form submission for ContactView.
        """
        mock_get_site_settings.return_value = self.mock_site_settings
        mock_get_about_content.return_value = self.mock_about_content

        mock_form_instance = mock_enquiry_form.return_value
        mock_form_instance.is_valid.return_value = False
        mock_form_instance.errors = {'email': ['Enter a valid email address.']}

        response = self.client.post(self.url, data={})

        mock_form_instance.is_valid.assert_called_once()
        mock_form_instance.save.assert_not_called()
        mock_send_mail.assert_not_called()
        self.assertEqual(response.status_code, 200) # Should re-render the form with errors
        self.assertTemplateUsed(response, 'core/information/contact.html')

        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), 'There was an error with your submission. Please correct the errors below.')
        self.assertIn('form', response.context)
        self.assertFalse(response.context['form'].is_valid())
        self.assertEqual(response.context['form'].errors, {'email': ['Enter a valid email address.']})
