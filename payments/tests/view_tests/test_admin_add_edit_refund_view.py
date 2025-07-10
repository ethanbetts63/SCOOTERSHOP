from django.test import TestCase, Client
from django.urls import reverse
from django.contrib import messages
from unittest.mock import patch, MagicMock
from payments.models import RefundRequest
from payments.forms.admin_refund_request_form import AdminRefundRequestForm
from payments.tests.test_helpers.model_factories import UserFactory, RefundRequestFactory, ServiceBookingFactory, SalesBookingFactory, PaymentFactory
from decimal import Decimal

class AdminAddEditRefundRequestViewTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.admin_user = UserFactory(is_staff=True)
        self.client.force_login(self.admin_user)
        self.add_url = reverse('payments:add_refund_request')
        self.service_booking = ServiceBookingFactory(payment_status='paid')
        self.sales_booking = SalesBookingFactory(payment_status='deposit_paid')
        self.payment = PaymentFactory()

    def test_get_add_refund_request(self):
        response = self.client.get(self.add_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'payments/admin_refund_form.html')
        self.assertIsInstance(response.context['form'], AdminRefundRequestForm)
        self.assertEqual(response.context['title'], 'Create New Refund Request')

    def test_get_edit_refund_request_service_booking(self):
        refund_request = RefundRequestFactory(service_booking=self.service_booking)
        edit_url = reverse('payments:edit_refund_request', kwargs={'pk': refund_request.pk})
        response = self.client.get(edit_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'payments/admin_refund_form.html')
        self.assertIsInstance(response.context['form'], AdminRefundRequestForm)
        self.assertEqual(response.context['form'].instance, refund_request)
        self.assertIn(f'Edit Service Refund Request for Booking {self.service_booking.service_booking_reference}', response.context['title'])

    def test_get_edit_refund_request_sales_booking(self):
        refund_request = RefundRequestFactory(sales_booking=self.sales_booking)
        edit_url = reverse('payments:edit_refund_request', kwargs={'pk': refund_request.pk})
        response = self.client.get(edit_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'payments/admin_refund_form.html')
        self.assertIsInstance(response.context['form'], AdminRefundRequestForm)
        self.assertEqual(response.context['form'].instance, refund_request)
        self.assertIn(f'Edit Sales Refund Request for Booking {self.sales_booking.sales_booking_reference}', response.context['title'])

    def test_get_edit_refund_request_invalid_pk(self):
        edit_url = reverse('payments:edit_refund_request', kwargs={'pk': 999999})
        response = self.client.get(edit_url)
        self.assertEqual(response.status_code, 404)

    @patch('django.contrib.messages.success')
    def test_post_add_valid_refund_request_service_booking(self, mock_messages_success):
        form_data = {
            'service_booking': self.service_booking.pk,
            'payment': self.payment.pk,
            'amount_to_refund': '50.00',
            'reason': 'Test Reason',
            'staff_notes': 'Test Staff Notes',
            'status': 'reviewed_pending_approval',
        }
        response = self.client.post(self.add_url, data=form_data)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('payments:admin_refund_management'))
        self.assertEqual(RefundRequest.objects.count(), 1)
        refund_request = RefundRequest.objects.first()
        self.assertTrue(refund_request.is_admin_initiated)
        self.assertEqual(refund_request.status, 'reviewed_pending_approval')
        mock_messages_success.assert_called_once()

    @patch('django.contrib.messages.success')
    def test_post_add_valid_refund_request_sales_booking(self, mock_messages_success):
        form_data = {
            'sales_booking': self.sales_booking.pk,
            'payment': self.payment.pk,
            'amount_to_refund': '50.00',
            'reason': 'Test Reason',
            'staff_notes': 'Test Staff Notes',
            'status': 'reviewed_pending_approval',
        }
        response = self.client.post(self.add_url, data=form_data)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('payments:admin_refund_management'))
        self.assertEqual(RefundRequest.objects.count(), 1)
        refund_request = RefundRequest.objects.first()
        self.assertTrue(refund_request.is_admin_initiated)
        self.assertEqual(refund_request.status, 'reviewed_pending_approval')
        mock_messages_success.assert_called_once()

    @patch('django.contrib.messages.success')
    def test_post_edit_valid_refund_request_service_booking(self, mock_messages_success):
        refund_request = RefundRequestFactory(service_booking=self.service_booking, payment=self.payment, amount_to_refund=Decimal('10.00'), reason='Old Reason', status='reviewed_pending_approval')
        edit_url = reverse('payments:edit_refund_request', kwargs={'pk': refund_request.pk})
        form_data = {
            'service_booking': self.service_booking.pk,
            'payment': self.payment.pk,
            'amount_to_refund': '20.00',
            'reason': 'New Reason',
            'staff_notes': 'New Staff Notes',
            'status': 'approved',
        }
        response = self.client.post(edit_url, data=form_data)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('payments:admin_refund_management'))
        refund_request.refresh_from_db()
        self.assertEqual(refund_request.amount_to_refund, Decimal('20.00'))
        self.assertEqual(refund_request.reason, 'New Reason')
        self.assertEqual(refund_request.status, 'approved')
        self.assertIsNotNone(refund_request.processed_by)
        self.assertIsNotNone(refund_request.processed_at)
        mock_messages_success.assert_called_once()

    @patch('django.contrib.messages.success')
    def test_post_edit_valid_refund_request_sales_booking(self, mock_messages_success):
        refund_request = RefundRequestFactory(sales_booking=self.sales_booking, payment=self.payment, amount_to_refund=Decimal('10.00'), reason='Old Reason', status='pending')
        edit_url = reverse('payments:edit_refund_request', kwargs={'pk': refund_request.pk})
        form_data = {
            'sales_booking': self.sales_booking.pk,
            'payment': self.payment.pk,
            'amount_to_refund': '20.00',
            'reason': 'New Reason',
            'staff_notes': 'New Staff Notes',
            'status': 'refunded',
        }
        response = self.client.post(edit_url, data=form_data)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('payments:admin_refund_management'))
        refund_request.refresh_from_db()
        self.assertEqual(refund_request.amount_to_refund, Decimal('20.00'))
        self.assertEqual(refund_request.reason, 'New Reason')
        self.assertEqual(refund_request.status, 'refunded')
        mock_messages_success.assert_called_once()

    @patch('django.contrib.messages.error')
    def test_post_add_invalid_refund_request(self, mock_messages_error):
        form_data = {
            'amount_to_refund': '-10.00',
            'reason': '',
        }
        response = self.client.post(self.add_url, data=form_data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'payments/admin_refund_form.html')
        self.assertIn('form', response.context)
        self.assertFalse(response.context['form'].is_valid())
        mock_messages_error.assert_called_once()

    @patch('django.contrib.messages.error')
    def test_post_edit_invalid_refund_request(self, mock_messages_error):
        refund_request = RefundRequestFactory(service_booking=self.service_booking, payment=self.payment)
        edit_url = reverse('payments:edit_refund_request', kwargs={'pk': refund_request.pk})
        form_data = {
            'amount_to_refund': '-10.00',
            'reason': '',
        }
        response = self.client.post(edit_url, data=form_data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'payments/admin_refund_form.html')
        self.assertIn('form', response.context)
        self.assertFalse(response.context['form'].is_valid())
        mock_messages_error.assert_called_once()

    def test_admin_required_mixin(self):
        self.client.logout()
        response = self.client.get(self.add_url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('users:login') + '?next=' + self.add_url)
