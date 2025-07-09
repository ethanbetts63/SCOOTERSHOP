from django.test import TestCase
from django.urls import reverse
from service.models import ServiceType
from service.tests.test_helpers.model_factories import ServiceTypeFactory, UserFactory
from django.contrib.messages import get_messages

class ServiceTypeDeleteViewTest(TestCase):

    def setUp(self):
        self.admin_user = UserFactory(is_staff=True)
        self.client.force_login(self.admin_user)
        self.service_type = ServiceTypeFactory(name='Test Service Type')

    def test_delete_service_type_post_success(self):
        initial_count = ServiceType.objects.count()
        response = self.client.post(reverse('service:delete_service_type', kwargs={'pk': self.service_type.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('service:service_types_management'))
        self.assertEqual(ServiceType.objects.count(), initial_count - 1)
        self.assertFalse(ServiceType.objects.filter(pk=self.service_type.pk).exists())
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), 'Service Type \'Test Service Type\' deleted successfully.')

    def test_delete_service_type_post_nonexistent(self):
        initial_count = ServiceType.objects.count()
        response = self.client.post(reverse('service:delete_service_type', kwargs={'pk': 999}))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(ServiceType.objects.count(), initial_count)

    def test_admin_required_mixin(self):
        self.client.logout()
        response = self.client.post(reverse('service:delete_service_type', kwargs={'pk': self.service_type.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('users:login') + '?next=' + reverse('service:delete_service_type', kwargs={'pk': self.service_type.pk}))