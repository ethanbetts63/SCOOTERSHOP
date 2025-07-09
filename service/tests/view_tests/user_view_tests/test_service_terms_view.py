from django.test import TestCase
from django.urls import reverse
from service.models import ServiceTerms
from service.tests.test_helpers.model_factories import ServiceTermsFactory

class ServiceTermsViewTest(TestCase):

    def test_service_terms_view_get_with_active_terms(self):
        active_terms = ServiceTermsFactory(is_active=True, content='Active Service Terms Content')
        # Ensure there are no other active terms
        ServiceTerms.objects.exclude(pk=active_terms.pk).update(is_active=False)

        response = self.client.get(reverse('service:service_booking_terms'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'service/service_terms.html')
        self.assertContains(response, 'Service Booking Terms &amp; Conditions')
        self.assertIn('terms', response.context)
        self.assertEqual(response.context['terms'], active_terms)
        self.assertContains(response, 'Active Service Terms Content')

    def test_service_terms_view_get_no_active_terms(self):
        ServiceTerms.objects.all().update(is_active=False) # Ensure no active terms

        response = self.client.get(reverse('service:service_booking_terms'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'service/service_terms.html')
        self.assertContains(response, 'Service Booking Terms &amp; Conditions')
        self.assertIn('terms', response.context)
        self.assertIsNone(response.context['terms'])

    def test_service_terms_view_get_multiple_active_terms(self):
        # This scenario should ideally not happen due to model's save method,
        # but testing robustness.
        active_terms1 = ServiceTermsFactory(is_active=True, content='First Active', version_number=1)
        active_terms2 = ServiceTermsFactory(is_active=True, content='Second Active', version_number=2)

        response = self.client.get(reverse('service:service_booking_terms'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'service/service_terms.html')
        self.assertIn('terms', response.context)
        # The view should return the first one it finds, which is usually the one with the highest version number due to default ordering
        self.assertIsNotNone(response.context['terms'])
        self.assertEqual(response.context['terms'], active_terms2) # Expecting the one with highest version_number
        self.assertContains(response, 'Second Active')