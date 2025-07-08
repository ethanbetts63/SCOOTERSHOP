
from django.test import TestCase
from django.urls import reverse
from unittest.mock import patch, MagicMock
from inventory.models import Motorcycle
from core.models import Enquiry
from inventory.tests.test_helpers.model_factories import MotorcycleFactory, UserFactory
from django.contrib.messages import get_messages
from django.conf import settings

class SalesEnquiryViewTest(TestCase):

    def setUp(self):
        self.motorcycle = MotorcycleFactory()
        self.user = UserFactory()
        self.client.force_login(self.user)

    def test_get_sales_enquiry_view(self):
        response = self.client.get(reverse('inventory:sales_enquiry', kwargs={'motorcycle_id': self.motorcycle.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'inventory/sales_enquiry.html')
        self.assertIn('form', response.context)
        self.assertIn('motorcycle', response.context)
        self.assertEqual(response.context['motorcycle'], self.motorcycle)
        self.assertEqual(response.context['form'].initial['motorcycle'], self.motorcycle)

    @patch('inventory.views.user_views.sales_enquiry_view.send_templated_email')
    @patch.object(settings, 'ADMIN_EMAIL', 'admin@example.com')
    def test_post_sales_enquiry_view_success(self, mock_send_email):
        initial_enquiry_count = Enquiry.objects.count()
        data = {
            'name': 'Test User',
            'email': 'test@example.com',
            'phone_number': '1234567890',
            'message': 'Interested in this bike.',
            'motorcycle': self.motorcycle.pk,
        }
        response = self.client.post(reverse('inventory:sales_enquiry', kwargs={'motorcycle_id': self.motorcycle.pk}), data=data)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('inventory:motorcycle-detail', kwargs={'pk': self.motorcycle.pk}))
        self.assertEqual(Enquiry.objects.count(), initial_enquiry_count + 1)
        
        enquiry = Enquiry.objects.latest('created_at')
        self.assertEqual(enquiry.motorcycle, self.motorcycle)
        self.assertEqual(enquiry.name, 'Test User')

        self.assertEqual(mock_send_email.call_count, 2)
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), 'Your enquiry has been sent successfully!')

    @patch('inventory.views.user_views.sales_enquiry_view.send_templated_email')
    def test_post_sales_enquiry_view_invalid(self, mock_send_email):
        initial_enquiry_count = Enquiry.objects.count()
        data = {
            'name': '',
            'email': 'invalid-email',
            'phone_number': '',
            'message': '',
            'motorcycle': self.motorcycle.pk,
        }
        response = self.client.post(reverse('inventory:sales_enquiry', kwargs={'motorcycle_id': self.motorcycle.pk}), data=data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'inventory/sales_enquiry.html')
        self.assertIn('form', response.context)
        self.assertFalse(response.context['form'].is_valid())
        self.assertEqual(Enquiry.objects.count(), initial_enquiry_count)
        mock_send_email.assert_not_called()
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 0) # No success message on invalid form
