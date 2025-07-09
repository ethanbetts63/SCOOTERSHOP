from django.test import TestCase
from django.urls import reverse
from payments.models import RefundRequest
from payments.tests.test_helpers.model_factories import RefundRequestFactory, UserFactory
from django.contrib.messages import get_messages

class IntermediaryRefundProcessingViewTest(TestCase):

    def setUp(self):
        self.admin_user = UserFactory(is_staff=True)
        self.client.force_login(self.admin_user)
        self.refund_request = RefundRequestFactory()

    def test_get_intermediary_refund_processing_view_success(self):
        response = self.client.get(reverse('payments:initiate_refund_process', kwargs={'pk': self.refund_request.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'payments/intermediary_refund_processing.html')
        self.assertIn('refund_request_pk', response.context)
        self.assertEqual(response.context['refund_request_pk'], self.refund_request.pk)
        self.assertIn('process_refund_url', response.context)
        self.assertEqual(response.context['process_refund_url'], reverse('payments:process_refund', kwargs={'pk': self.refund_request.pk}))

    

    def test_get_intermediary_refund_processing_view_invalid_pk(self):
        response = self.client.get(reverse('payments:initiate_refund_process', kwargs={'pk': 999}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'payments/intermediary_refund_processing.html')
        # messages = list(get_messages(response.wsgi_request))
        # self.assertEqual(len(messages), 1)
        # self.assertIn('Refund request not found or invalid.', str(messages[0]))
        self.assertEqual(response.context['refund_request_pk'], 999)

    def test_admin_required_mixin(self):
        self.client.logout()
        response = self.client.get(reverse('payments:initiate_refund_process', kwargs={'pk': self.refund_request.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('users:login') + '?next=' + reverse('payments:initiate_refund_process', kwargs={'pk': self.refund_request.pk}))