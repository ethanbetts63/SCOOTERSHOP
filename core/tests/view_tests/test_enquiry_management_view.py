from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from core.tests.test_helpers.model_factories import EnquiryFactory

User = get_user_model()

class EnquiryManagementViewTest(TestCase):
    """
    Tests for the EnquiryManagementView (admin view).
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
        # Create 15 enquiries to test pagination (paginate_by = 10)
        for i in range(15):
            EnquiryFactory()

    def setUp(self):
        self.url = reverse('core:enquiry_management')

    def test_admin_required_mixin_redirects_non_admin(self):
        """
        Test that non-admin users are redirected from the enquiry management view.
        """
        self.client.login(username='user', password='password')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302) # Redirect to login or permission denied

    def test_admin_user_can_access_view(self):
        """
        Test that admin users can access the enquiry management view.
        """
        self.client.login(username='admin', password='password')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/admin/enquiry_management.html')
        self.assertContains(response, 'Enquiry Management')

    def test_enquiries_context_object(self):
        """
        Test that the 'enquiries' context object contains the correct data and ordering.
        """
        self.client.login(username='admin', password='password')
        response = self.client.get(self.url)
        self.assertIn('enquiries', response.context)
        enquiries = response.context['enquiries']
        self.assertEqual(len(enquiries), 10) # paginate_by is 10
        # Verify ordering by created_at descending
        self.assertTrue(all(enquiries[i].created_at >= enquiries[i+1].created_at for i in range(len(enquiries) - 1)))

    def test_pagination(self):
        """
        Test that pagination works correctly.
        """
        self.client.login(username='admin', password='password')
        response = self.client.get(self.url)
        self.assertEqual(len(response.context['enquiries']), 10)

        response = self.client.get(f'{self.url}?page=2')
        self.assertEqual(len(response.context['enquiries']), 5) # 15 total, 10 on first page, 5 on second

    def test_post_method_not_allowed(self):
        """
        Test that POST requests to the enquiry management view are not allowed.
        """
        self.client.login(username='admin', password='password')
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 405) # Method Not Allowed
