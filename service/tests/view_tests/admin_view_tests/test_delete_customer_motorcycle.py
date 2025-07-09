

from django.test import TestCase
from django.urls import reverse
from service.models import CustomerMotorcycle
from service.tests.test_helpers.model_factories import CustomerMotorcycleFactory, UserFactory
from django.contrib.messages import get_messages

class CustomerMotorcycleDeleteViewTest(TestCase):

    def setUp(self):
        self.admin_user = UserFactory(is_staff=True)
        self.client.force_login(self.admin_user)
        self.customer_motorcycle = CustomerMotorcycleFactory(year=2020, brand='Honda', model='CBR')

    def test_delete_customer_motorcycle_post_success(self):
        initial_count = CustomerMotorcycle.objects.count()
        response = self.client.post(reverse('service:admin_delete_customer_motorcycle', kwargs={'pk': self.customer_motorcycle.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('service:admin_customer_motorcycle_management'))
        self.assertEqual(CustomerMotorcycle.objects.count(), initial_count - 1)
        self.assertFalse(CustomerMotorcycle.objects.filter(pk=self.customer_motorcycle.pk).exists())
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), 'Motorcycle \'2020 Honda CBR\' deleted successfully.')

    def test_delete_customer_motorcycle_post_nonexistent(self):
        initial_count = CustomerMotorcycle.objects.count()
        response = self.client.post(reverse('service:admin_delete_customer_motorcycle', kwargs={'pk': 999}))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(CustomerMotorcycle.objects.count(), initial_count)

    def test_admin_required_mixin(self):
        self.client.logout()
        response = self.client.post(reverse('service:admin_delete_customer_motorcycle', kwargs={'pk': self.customer_motorcycle.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('users:login') + '?next=' + reverse('service:admin_delete_customer_motorcycle', kwargs={'pk': self.customer_motorcycle.pk}))
