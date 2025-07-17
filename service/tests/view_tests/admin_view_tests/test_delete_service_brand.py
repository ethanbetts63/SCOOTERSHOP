from django.test import TestCase
from django.urls import reverse
from service.models import ServiceBrand
from users.tests.test_helpers.model_factories import UserFactory, StaffUserFactory
from service.tests.test_helpers.model_factories import ServiceBookingFactory, ServiceProfileFactory, ServiceTypeFactory, ServiceSettingsFactory, ServiceTermsFactory, ServicefaqFactory, CustomerMotorcycleFactory, BlockedServiceDateFactory, ServiceBrandFactory
from inventory.tests.test_helpers.model_factories import SalesBookingFactory, SalesProfileFactory
from payments.tests.test_helpers.model_factories import PaymentFactory, WebhookEventFactory
from refunds.tests.test_helpers.model_factories import RefundRequestFactory, RefundSettingsFactory
from django.contrib.messages import get_messages

class ServiceBrandDeleteViewTest(TestCase):

    def setUp(self):
        self.admin_user = UserFactory(is_staff=True)
        self.client.force_login(self.admin_user)
        self.service_brand = ServiceBrandFactory(name='Test Brand')

    def test_delete_service_brand_post_success(self):
        initial_count = ServiceBrand.objects.count()
        response = self.client.post(reverse('service:delete_service_brand', kwargs={'pk': self.service_brand.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('service:service_brands_management'))
        self.assertEqual(ServiceBrand.objects.count(), initial_count - 1)
        self.assertFalse(ServiceBrand.objects.filter(pk=self.service_brand.pk).exists())
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), 'Service brand \'Test Brand\' deleted successfully.')

    def test_delete_service_brand_post_nonexistent(self):
        initial_count = ServiceBrand.objects.count()
        response = self.client.post(reverse('service:delete_service_brand', kwargs={'pk': 999}))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(ServiceBrand.objects.count(), initial_count)

    def test_admin_required_mixin(self):
        self.client.logout()
        response = self.client.post(reverse('service:delete_service_brand', kwargs={'pk': self.service_brand.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('users:login') + '?next=' + reverse('service:delete_service_brand', kwargs={'pk': self.service_brand.pk}))