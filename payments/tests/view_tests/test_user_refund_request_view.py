from django.test import TestCase, Client
from django.urls import reverse
from django.contrib import messages
from unittest.mock import patch, MagicMock
from payments.models import RefundRequest
from payments.forms.user_refund_request_form import RefundRequestForm
from payments.tests.test_helpers.model_factories import ServiceBookingFactory, SalesBookingFactory, PaymentFactory, UserFactory, ServiceProfileFactory, SalesProfileFactory
from django.utils import timezone
import uuid

class UserRefundRequestViewTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.url = reverse('payments:user_refund_request')
        self.service_booking = ServiceBookingFactory()
        self.sales_booking = SalesBookingFactory()
        self.payment = PaymentFactory()
        self.user = UserFactory()
        self.service_profile = ServiceProfileFactory(user=self.user)
        self.sales_profile = SalesProfileFactory(user=self.user)

    def test_get_request(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'payments/user_refund_request.html')
        self.assertIsInstance(response.context['form'], RefundRequestForm)
        self.assertEqual(response.context['page_title'], 'Request a Refund')
        self.assertIn('Please enter your booking details', response.context['intro_text'])

    @patch('payments.views.Refunds.user_refund_request_view.send_templated_email')
    @patch('django.contrib.messages.success')
    @patch('django.utils.timezone.now')
    @patch('uuid.uuid4')
    def test_post_valid_refund_request_service_booking(self, mock_uuid4, mock_now, mock_messages_success, mock_send_templated_email):
        mock_uuid4.return_value = uuid.UUID('12345678-1234-5678-1234-567812345678')
        mock_now.return_value = timezone.now()

        form_data = {
            'booking_reference': self.service_booking.service_booking_reference,
            'email': self.user.email,
            'reason': 'Test Reason for Service Booking',
        }
        response = self.client.post(self.url, data=form_data)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('payments:user_confirmation_refund_request'))

        self.assertEqual(RefundRequest.objects.count(), 1)
        refund_request = RefundRequest.objects.first()
        self.assertEqual(refund_request.service_booking, self.service_booking)
        self.assertEqual(refund_request.request_email, self.user.email)
        self.assertEqual(refund_request.reason, 'Test Reason for Service Booking')
        self.assertEqual(refund_request.status, 'unverified')
        self.assertEqual(str(refund_request.verification_token), str(mock_uuid4.return_value))
        self.assertEqual(refund_request.token_created_at, mock_now.return_value)

        mock_send_templated_email.assert_called_once()
        mock_messages_success.assert_called_once()

    @patch('payments.views.Refunds.user_refund_request_view.send_templated_email')
    @patch('django.contrib.messages.success')
    @patch('django.utils.timezone.now')
    @patch('uuid.uuid4')
    def test_post_valid_refund_request_sales_booking(self, mock_uuid4, mock_now, mock_messages_success, mock_send_templated_email):
        mock_uuid4.return_value = uuid.UUID('87654321-4321-8765-4321-876543218765')
        mock_now.return_value = timezone.now()

        form_data = {
            'booking_reference': self.sales_booking.sales_booking_reference,
            'email': self.user.email,
            'reason': 'Test Reason for Sales Booking',
        }
        response = self.client.post(self.url, data=form_data)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('payments:user_confirmation_refund_request'))

        self.assertEqual(RefundRequest.objects.count(), 1)
        refund_request = RefundRequest.objects.first()
        self.assertEqual(refund_request.sales_booking, self.sales_booking)
        self.assertEqual(refund_request.request_email, self.user.email)
        self.assertEqual(refund_request.reason, 'Test Reason for Sales Booking')
        self.assertEqual(refund_request.status, 'unverified')
        self.assertEqual(str(refund_request.verification_token), str(mock_uuid4.return_value))
        self.assertEqual(refund_request.token_created_at, mock_now.return_value)

        mock_send_templated_email.assert_called_once()
        mock_messages_success.assert_called_once()

    @patch('django.contrib.messages.error')
    @patch('payments.views.Refunds.user_refund_request_view.send_templated_email')
    def test_post_invalid_refund_request(self, mock_send_templated_email, mock_messages_error):
        form_data = {
            'booking_reference': 'INVALID-REF',
            'email': 'invalid-email',
            'reason': '',
        }
        response = self.client.post(self.url, data=form_data)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'payments/user_refund_request.html')
        self.assertIn('form', response.context)
        self.assertFalse(response.context['form'].is_valid())
        self.assertEqual(RefundRequest.objects.count(), 0)
        mock_send_templated_email.assert_not_called()
        mock_messages_error.assert_called_once()
