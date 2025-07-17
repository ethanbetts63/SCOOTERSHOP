from django.test import TestCase
from django.urls import reverse
from service.models import ServiceTerms
from users.tests.test_helpers.model_factories import UserFactory, StaffUserFactory
from service.tests.test_helpers.model_factories import ServiceBookingFactory, ServiceProfileFactory, ServiceTypeFactory, ServiceSettingsFactory, ServiceTermsFactory, ServicefaqFactory, CustomerMotorcycleFactory, BlockedServiceDateFactory, ServiceBrandFactory
from inventory.tests.test_helpers.model_factories import SalesBookingFactory, SalesProfileFactory
from payments.tests.test_helpers.model_factories import PaymentFactory, WebhookEventFactory
from refunds.tests.test_helpers.model_factories import RefundRequestFactory, RefundSettingsFactory

class ServiceTermsManagementViewTest(TestCase):

    def setUp(self):
        self.admin_user = UserFactory(is_staff=True)
        self.client.force_login(self.admin_user)

        # Create some ServiceTerms versions
        self.terms_v1 = ServiceTermsFactory(version_number=1, is_active=False)
        self.terms_v2 = ServiceTermsFactory(version_number=2, is_active=True)
        self.terms_v3 = ServiceTermsFactory(version_number=3, is_active=False)

        # Create a service booking linked to a terms version
        ServiceBookingFactory(service_terms_version=self.terms_v2)

    def test_service_terms_management_view_get(self):
        response = self.client.get(reverse('service:service_terms_management'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'service/admin_service_terms_management.html')
        self.assertContains(response, 'Service Terms & Conditions Management')
        self.assertIn('terms_versions', response.context)

        # Check ordering (by -version_number)
        terms_versions = list(response.context['terms_versions'])
        self.assertEqual(terms_versions[0], self.terms_v3)
        self.assertEqual(terms_versions[1], self.terms_v2)
        self.assertEqual(terms_versions[2], self.terms_v1)

        # Check booking_count annotation
        self.assertEqual(terms_versions[1].booking_count, 1) # terms_v2 has 1 booking
        self.assertEqual(terms_versions[0].booking_count, 0) # terms_v3 has 0 bookings

    def test_service_terms_management_view_pagination(self):
        # Create more terms to test pagination
        for i in range(4, 15):
            ServiceTermsFactory(version_number=i)
        
        response = self.client.get(reverse('service:service_terms_management') + '?page=2')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'service/admin_service_terms_management.html')
        self.assertIn('terms_versions', response.context)
        self.assertEqual(len(response.context['terms_versions']), 4) # 14 total terms, 10 on first page, 4 on second

    def test_admin_required_mixin(self):
        self.client.logout()
        response = self.client.get(reverse('service:service_terms_management'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('users:login') + '?next=' + reverse('service:service_terms_management'))