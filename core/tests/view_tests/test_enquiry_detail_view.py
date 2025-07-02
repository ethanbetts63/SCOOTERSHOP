from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from core.tests.test_helpers.model_factories import EnquiryFactory

User = get_user_model()

class EnquiryDetailViewTest(TestCase):
    """
    Tests for the EnquiryDetailView (admin view).
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
        cls.enquiry = EnquiryFactory()

    def setUp(self):
        self.url = reverse('core:enquiry_detail', args=[self.enquiry.pk])

    def test_admin_required_mixin_redirects_non_admin(self):
        """
        Test that non-admin users are redirected from the enquiry detail view.
        """
        self.client.login(username='user', password='password')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302) # Redirect to login or permission denied

    def test_admin_user_can_access_view(self):
        """
        Test that admin users can access the enquiry detail view.
        """
        self.client.login(username='admin', password='password')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/admin/enquiry_detail.html')
        self.assertContains(response, 'Enquiry Details')
        self.assertContains(response, self.enquiry.name)
        self.assertContains(response, self.enquiry.email)

    def test_enquiry_context_object(self):
        """
        Test that the 'enquiry' context object contains the correct data.
        """
        self.client.login(username='admin', password='password')
        response = self.client.get(self.url)
        self.assertIn('enquiry', response.context)
        self.assertEqual(response.context['enquiry'], self.enquiry)

    def test_enquiry_not_found(self):
        """
        Test that a 404 is returned for a non-existent enquiry.
        """
        self.client.login(username='admin', password='password')
        non_existent_url = reverse('core:admin_enquiry_detail', args=[99999])
        response = self.client.get(non_existent_url)
        self.assertEqual(response.status_code, 404)

    def test_post_method_not_allowed(self):
        """
        Test that POST requests to the enquiry detail view are not allowed.
        """
        self.client.login(username='admin', password='password')
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 405) # Method Not Allowed
