from django.test import TestCase
from django.urls import reverse
from inventory.models import Salesfaq
from inventory.tests.test_helpers.model_factories import SalesfaqFactory, UserFactory
from django.contrib.messages import get_messages

class SalesfaqDeleteViewTest(TestCase):

    def setUp(self):
        self.admin_user = UserFactory(is_staff=True)
        self.client.force_login(self.admin_user)
        self.sales_faq = SalesfaqFactory(question='Test FAQ Question')

    

    def test_sales_faq_delete_post_success(self):
        initial_count = Salesfaq.objects.count()
        response = self.client.post(reverse('inventory:sales_faq_delete', kwargs={'pk': self.sales_faq.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('inventory:sales_faq_management'))
        self.assertEqual(Salesfaq.objects.count(), initial_count - 1)
        self.assertFalse(Salesfaq.objects.filter(pk=self.sales_faq.pk).exists())
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertIn('The faq \'Test FAQ Question...\' was deleted successfully.', str(messages[0]))

    def test_sales_faq_delete_post_nonexistent(self):
        initial_count = Salesfaq.objects.count()
        response = self.client.post(reverse('inventory:sales_faq_delete', kwargs={'pk': 999}))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(Salesfaq.objects.count(), initial_count)

    def test_admin_required_mixin(self):
        self.client.logout()
        response = self.client.get(reverse('inventory:sales_faq_delete', kwargs={'pk': self.sales_faq.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('users:login') + '?next=' + reverse('inventory:sales_faq_delete', kwargs={'pk': self.sales_faq.pk}))