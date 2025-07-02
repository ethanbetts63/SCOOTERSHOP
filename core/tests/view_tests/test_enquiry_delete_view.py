from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from core.tests.test_helpers.model_factories import EnquiryFactory
from core.models.enquiry import Enquiry
from unittest.mock import patch
from django.contrib.messages import get_messages

User = get_user_model()

class EnquiryDeleteViewTest(TestCase):
    """
    Tests for the EnquiryDeleteView (admin view).
    """

    @classmethod
    def setUpTestData(cls):
        cls.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='password'
        )
        cls.regular_user = User.objects.create_user(
            username='user',
            email='user@example.com',
            password='password'
        )

    def setUp(self):
        self.enquiry = EnquiryFactory() # Create a new enquiry for each test
        self.url = reverse('core:enquiry_delete', args=[self.enquiry.pk])
        self.management_url = reverse('core:enquiry_management')

    def test_admin_required_mixin_redirects_non_admin(self):
        """
        Test that non-admin users are redirected from the enquiry delete view.
        """
        self.client.login(username='user', password='password')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302) # Redirect to login or permission denied

    def test_get_redirects_with_message(self):
        """
        Test that a GET request to the delete view redirects to management with a message.
        """
        self.client.login(username='admin', password='password')
        response = self.client.get(self.url)
        self.assertRedirects(response, self.management_url)
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Please confirm deletion via the management page.")
        self.assertTrue(Enquiry.objects.filter(pk=self.enquiry.pk).exists()) # Ensure not deleted by GET

    @patch('django.contrib.messages.success')
    def test_post_deletes_enquiry_and_redirects(self, mock_messages_success):
        """
        Test that a POST request to the delete view deletes the enquiry and redirects.
        """
        self.client.login(username='admin', password='password')
        response = self.client.post(self.url)
        self.assertRedirects(response, self.management_url)
        self.assertFalse(Enquiry.objects.filter(pk=self.enquiry.pk).exists())
        mock_messages_success.assert_called_once_with(self.client.request, f"Enquiry from {self.enquiry.name} was deleted successfully.")

    def test_post_enquiry_not_found(self):
        """
        Test that a POST request for a non-existent enquiry returns 404.
        """
        self.client.login(username='admin', password='password')
        non_existent_url = reverse('core:admin_enquiry_delete', args=[99999])
        response = self.client.post(non_existent_url)
        self.assertEqual(response.status_code, 404)
