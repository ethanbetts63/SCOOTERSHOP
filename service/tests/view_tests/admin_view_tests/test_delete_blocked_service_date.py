from django.test import TestCase
from django.urls import reverse
from service.models import BlockedServiceDate
from service.tests.test_helpers.model_factories import BlockedServiceDateFactory, UserFactory
from django.contrib.messages import get_messages

class BlockedServiceDateDeleteViewTest(TestCase):

    def setUp(self):
        self.admin_user = UserFactory(is_staff=True)
        self.client.force_login(self.admin_user)
        self.blocked_date = BlockedServiceDateFactory()

    def test_delete_blocked_service_date_post_success(self):
        initial_count = BlockedServiceDate.objects.count()
        response = self.client.post(reverse('service:delete_blocked_service_date', kwargs={'pk': self.blocked_date.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('service:blocked_service_dates_management'))
        self.assertEqual(BlockedServiceDate.objects.count(), initial_count - 1)
        self.assertFalse(BlockedServiceDate.objects.filter(pk=self.blocked_date.pk).exists())
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), 'Blocked service date deleted successfully!')

    def test_delete_blocked_service_date_post_nonexistent(self):
        initial_count = BlockedServiceDate.objects.count()
        response = self.client.post(reverse('service:delete_blocked_service_date', kwargs={'pk': 999}))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(BlockedServiceDate.objects.count(), initial_count)

    def test_admin_required_mixin(self):
        self.client.logout()
        response = self.client.post(reverse('service:delete_blocked_service_date', kwargs={'pk': self.blocked_date.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('users:login') + '?next=' + reverse('service:delete_blocked_service_date', kwargs={'pk': self.blocked_date.pk}))