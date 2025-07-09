from django.test import TestCase
from django.urls import reverse
from service.models import ServiceBrand
from service.tests.test_helpers.model_factories import ServiceBrandFactory, UserFactory
from django.contrib.messages import get_messages

class ServiceBrandManagementViewTest(TestCase):

    def setUp(self):
        self.admin_user = UserFactory(is_staff=True)
        self.client.force_login(self.admin_user)
        self.brand1 = ServiceBrandFactory(name='Brand A')
        self.brand2 = ServiceBrandFactory(name='Brand B')

    def test_get_service_brand_management_view(self):
        response = self.client.get(reverse('service:service_brands_management'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'service/service_brands_management.html')
        self.assertContains(response, 'Manage Service Brands')
        self.assertIn('service_brands', response.context)
        self.assertEqual(list(response.context['service_brands']), [self.brand1, self.brand2])

    def test_get_service_brand_management_view_edit_mode(self):
        response = self.client.get(reverse('service:service_brands_management') + f'?edit_brand_pk={self.brand1.pk}')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'service/service_brands_management.html')
        self.assertIn('edit_brand', response.context)
        self.assertEqual(response.context['edit_brand'], self.brand1)
        self.assertIn('form', response.context)
        self.assertEqual(response.context['form'].instance, self.brand1)

    def test_post_add_brand_success(self):
        initial_count = ServiceBrand.objects.count()
        data = {
            'name': 'Brand C',
            'add_brand_submit': ''
        }
        response = self.client.post(reverse('service:service_brands_management'), data=data)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('service:service_brands_management'))
        self.assertEqual(ServiceBrand.objects.count(), initial_count + 1)
        self.assertTrue(ServiceBrand.objects.filter(name='Brand C').exists())
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertIn('Service brand \'Brand C\' added successfully.', str(messages[0]))

    def test_post_update_brand_success(self):
        initial_name = self.brand1.name
        data = {
            'brand_id': self.brand1.pk,
            'name': 'Updated Brand A',
            'add_brand_submit': ''
        }
        response = self.client.post(reverse('service:service_brands_management'), data=data)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('service:service_brands_management'))
        self.brand1.refresh_from_db()
        self.assertEqual(self.brand1.name, 'Updated Brand A')
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertIn(f'Service brand \'Updated Brand A\' updated successfully.', str(messages[0]))

    def test_post_add_brand_invalid(self):
        initial_count = ServiceBrand.objects.count()
        data = {
            'name': '',
            'add_brand_submit': ''
        }
        response = self.client.post(reverse('service:service_brands_management'), data=data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'service/service_brands_management.html')
        self.assertContains(response, 'Please correct the errors below.')
        self.assertIn('form', response.context)
        self.assertFalse(response.context['form'].is_valid())
        self.assertEqual(ServiceBrand.objects.count(), initial_count)

    def test_admin_required_mixin(self):
        self.client.logout()
        response = self.client.get(reverse('service:service_brands_management'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('users:login') + '?next=' + reverse('service:service_brands_management'))