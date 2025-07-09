from django.test import TestCase
from django.urls import reverse
from service.models import ServiceTerms
from service.tests.test_helpers.model_factories import ServiceTermsFactory, UserFactory

class ServiceTermsDetailsViewTest(TestCase):

    def setUp(self):
        self.admin_user = UserFactory(is_staff=True)
        self.client.force_login(self.admin_user)
        self.service_terms = ServiceTermsFactory(version_number=1, content='Test Content')

    def test_service_terms_details_view_get(self):
        response = self.client.get(reverse('service:service_terms_detail', kwargs={'pk': self.service_terms.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'service/admin_service_terms_details.html')
        self.assertContains(response, f'View Service T&C Version {self.service_terms.version_number}')
        self.assertIn('terms_version', response.context)
        self.assertEqual(response.context['terms_version'], self.service_terms)

    def test_service_terms_details_view_nonexistent(self):
        response = self.client.get(reverse('service:service_terms_detail', kwargs={'pk': 999}))
        self.assertEqual(response.status_code, 404)

    def test_admin_required_mixin(self):
        self.client.logout()
        response = self.client.get(reverse('service:service_terms_detail', kwargs={'pk': self.service_terms.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('users:login') + '?next=' + reverse('service:service_terms_detail', kwargs={'pk': self.service_terms.pk}))