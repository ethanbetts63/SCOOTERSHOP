from django.test import TestCase, Client
from django.urls import reverse
from core.models.enquiry import Enquiry
from ...test_helpers.model_factories import UserFactory, EnquiryFactory

class EnquiryManagementViewTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.staff_user = UserFactory(is_staff=True)
        cls.regular_user = UserFactory()
        cls.login_url = reverse('users:login')
        cls.list_url = reverse('core:enquiry_management')

       

        for i in range(15):
            EnquiryFactory()

    def setUp(self):
        self.client = Client()

    def test_anonymous_user_redirected(self):
        response = self.client.get(self.list_url)
        self.assertRedirects(response, f'{self.login_url}?next={self.list_url}')

    def test_regular_user_redirected(self):
        self.client.force_login(self.regular_user)
        response = self.client.get(self.list_url)
        self.assertRedirects(response, f'{self.login_url}?next={self.list_url}')

    def test_staff_user_can_access_view(self):
        self.client.force_login(self.staff_user)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/admin/enquiry_management.html')

    def test_view_lists_enquiries_and_paginates(self):
        self.client.force_login(self.staff_user)
        response = self.client.get(self.list_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('enquiries', response.context)
        self.assertIn('page_obj', response.context)
        self.assertTrue(response.context['page_obj'].has_next())
        self.assertEqual(len(response.context['enquiries']), 10)

        self.assertEqual(response.context['page_title'], "Enquiry Management")

       

        enquiries_in_context = response.context['enquiries']
        all_enquiries = list(Enquiry.objects.all().order_by('-created_at'))
        self.assertListEqual(list(enquiries_in_context), all_enquiries[:10])

    def test_pagination_page_2(self):
        self.client.force_login(self.staff_user)
        response = self.client.get(f'{self.list_url}?page=2')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['enquiries']), 5)
