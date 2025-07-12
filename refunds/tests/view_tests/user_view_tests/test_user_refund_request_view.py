from django.test import TestCase, Client
from django.urls import reverse
from django.contrib import messages
from unittest.mock import patch, MagicMock
from refunds.models import RefundRequest
from payments.forms.user_refund_request_form import RefundRequestForm
from payments.tests.test_helpers.model_factories import ServiceBookingFactory, SalesBookingFactory, PaymentFactory, UserFactory, ServiceProfileFactory, SalesProfileFactory
from django.utils import timezone
import uuid

class UserRefundRequestViewTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.url = reverse('payments:user_refund_request')
        self.payment = PaymentFactory(status='succeeded')
        self.user = UserFactory()
        self.service_profile = ServiceProfileFactory(user=self.user)
        self.sales_profile = SalesProfileFactory(user=self.user)
        self.service_booking = ServiceBookingFactory(payment=self.payment, service_profile=self.service_profile)
        self.sales_booking = SalesBookingFactory(payment=self.payment, sales_profile=self.sales_profile)

    def test_get_request(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'payments/user_refund_request.html')
        self.assertIsInstance(response.context['form'], RefundRequestForm)
        self.assertEqual(response.context['page_title'], 'Request a Refund')
        self.assertIn('Please enter your booking details', response.context['intro_text'])

    @patch('payments.views.Refunds.user_refund_request_view.send_templated_email')
    @patch('django.contrib.messages.success')
    @patch('uuid.uuid4')
    def test_post_valid_refund_request_service_booking(self, mock_uuid4, mock_messages_success, mock_send_templated_email):
        mock_uuid4.return_value = uuid.UUID('12345678-1234-5678-1234-567812345678')

        form_data = {
            'booking_reference': self.service_booking.service_booking_reference,
            'email': self.service_profile.email,
            'reason': 'Test Reason for Service Booking',
        }
        response = self.client.post(self.url, data=form_data)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('payments:user_confirmation_refund_request'))

        self.assertEqual(RefundRequest.objects.count(), 1)
        refund_request = RefundRequest.objects.first()
        self.assertEqual(refund_request.service_booking, self.service_booking)
        self.assertEqual(refund_request.request_email, self.service_profile.email)
        self.assertEqual(refund_request.reason, 'Test Reason for Service Booking')
        self.assertEqual(refund_request.status, 'unverified')
        self.assertEqual(str(refund_request.verification_token), str(mock_uuid4.return_value))

        mock_send_templated_email.assert_called_once()
        mock_messages_success.assert_called_once()

    @patch('payments.views.Refunds.user_refund_request_view.send_templated_email')
    @patch('django.contrib.messages.success')
    @patch('uuid.uuid4')
    def test_post_valid_refund_request_sales_booking(self, mock_uuid4, mock_messages_success, mock_send_templated_email):
        mock_uuid4.return_value = uuid.UUID('87654321-4321-8765-4321-876543218765')

        form_data = {
            'booking_reference': self.sales_booking.sales_booking_reference,
            'email': self.sales_profile.email,
            'reason': 'Test Reason for Sales Booking',
        }
        response = self.client.post(self.url, data=form_data)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('payments:user_confirmation_refund_request'))

        self.assertEqual(RefundRequest.objects.count(), 1)
        refund_request = RefundRequest.objects.first()
        self.assertEqual(refund_request.sales_booking, self.sales_booking)
        self.assertEqual(refund_request.request_email, self.sales_profile.email)
        self.assertEqual(refund_request.reason, 'Test Reason for Sales Booking')
        self.assertEqual(refund_request.status, 'unverified')
        self.assertEqual(str(refund_request.verification_token), str(mock_uuid4.return_value))

        mock_send_templated_email.assert_called_once()
        mock_messages_success.assert_called_once()

    def test_post_invalid_refund_request(self):
        form_data = {
            'booking_reference': 'INVALID-REF',
            'email': 'invalid-email',
            'reason': '',
        }
        response = self.client.post(self.url, data=form_data)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'payments/user_refund_request.html')
        self.assertIn('form', response.context)
        form = response.context['form']
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)
