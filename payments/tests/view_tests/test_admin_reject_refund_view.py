from django.test import TestCase, Client
from django.urls import reverse
from django.contrib import messages
from unittest.mock import patch, MagicMock
from payments.models import RefundRequest
from payments.forms.admin_reject_refund_form import AdminRejectRefundForm
from payments.tests.test_helpers.model_factories import UserFactory, RefundRequestFactory, ServiceBookingFactory, SalesBookingFactory, ServiceProfileFactory, SalesProfileFactory
from django.utils import timezone

class AdminRejectRefundViewTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.admin_user = UserFactory(is_staff=True)
        self.client.force_login(self.admin_user)
        self.service_booking = ServiceBookingFactory()
        self.sales_booking = SalesBookingFactory()
        self.refund_request_service = RefundRequestFactory(service_booking=self.service_booking, status='pending')
        self.refund_request_sales = RefundRequestFactory(sales_booking=self.sales_booking, status='pending')

    def test_get_reject_refund_request_service_booking(self):
        url = reverse('payments:reject_refund_request', kwargs={'pk': self.refund_request_service.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'payments/admin_reject_refund_form.html')
        self.assertIsInstance(response.context['form'], AdminRejectRefundForm)
        self.assertEqual(response.context['refund_request'], self.refund_request_service)
        self.assertIn(f'Reject Refund Request for Booking {self.service_booking.service_booking_reference}', response.context['title'])

    def test_get_reject_refund_request_sales_booking(self):
        url = reverse('payments:reject_refund_request', kwargs={'pk': self.refund_request_sales.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'payments/admin_reject_refund_form.html')
        self.assertIsInstance(response.context['form'], AdminRejectRefundForm)
        self.assertEqual(response.context['refund_request'], self.refund_request_sales)
        self.assertIn(f'Reject Refund Request for Booking {self.sales_booking.sales_booking_reference}', response.context['title'])

    def test_get_reject_refund_request_invalid_pk(self):
        url = reverse('payments:reject_refund_request', kwargs={'pk': '99999999-9999-9999-9999-999999999999'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    @patch('payments.views.Refunds.admin_reject_refund_view.send_templated_email')
    @patch('django.contrib.messages.success')
    @patch('django.contrib.messages.info')
    @patch('django.utils.timezone.now')
    def test_post_reject_refund_request_send_email_to_user(self, mock_now, mock_messages_info, mock_messages_success, mock_send_templated_email):
        mock_now.return_value = timezone.now()
        url = reverse('payments:reject_refund_request', kwargs={'pk': self.refund_request_service.pk})
        form_data = {
            'rejection_reason': 'Test rejection reason',
            'send_rejection_email': True,
        }
        response = self.client.post(url, data=form_data)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('payments:admin_refund_management'))

        self.refund_request_service.refresh_from_db()
        self.assertEqual(self.refund_request_service.status, 'rejected')
        self.assertEqual(self.refund_request_service.rejection_reason, 'Test rejection reason')
        self.assertEqual(self.refund_request_service.processed_by, self.admin_user)
        self.assertEqual(self.refund_request_service.processed_at, mock_now.return_value)

        mock_messages_success.assert_called_once_with(mock.ANY, f"Refund Request for booking '{self.service_booking.service_booking_reference}' has been successfully rejected.")
        self.assertEqual(mock_send_templated_email.call_count, 2) # One for user, one for admin

        # Check user email call
        user_email_call = mock_send_templated_email.call_args_list[0]
        self.assertEqual(user_email_call.kwargs['recipient_list'], [self.refund_request_service.request_email])
        self.assertIn('Your Refund Request for Booking', user_email_call.kwargs['subject'])
        self.assertEqual(user_email_call.kwargs['template_name'], 'user_refund_request_rejected.html')
        mock_messages_info.assert_any_call(mock.ANY, "Automated rejection email sent to the user.")

        # Check admin email call
        admin_email_call = mock_send_templated_email.call_args_list[1]
        self.assertEqual(admin_email_call.kwargs['recipient_list'], [settings.DEFAULT_FROM_EMAIL])
        self.assertIn('Refund Request', admin_email_call.kwargs['subject'])
        self.assertEqual(admin_email_call.kwargs['template_name'], 'admin_refund_request_rejected.html')
        mock_messages_info.assert_any_call(mock.ANY, "Admin notification email sent regarding the rejection.")

    @patch('payments.views.Refunds.admin_reject_refund_view.send_templated_email')
    @patch('django.contrib.messages.success')
    @patch('django.contrib.messages.info')
    @patch('django.utils.timezone.now')
    def test_post_reject_refund_request_do_not_send_email_to_user(self, mock_now, mock_messages_info, mock_messages_success, mock_send_templated_email):
        mock_now.return_value = timezone.now()
        url = reverse('payments:reject_refund_request', kwargs={'pk': self.refund_request_service.pk})
        form_data = {
            'rejection_reason': 'Test rejection reason',
            'send_rejection_email': False,
        }
        response = self.client.post(url, data=form_data)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('payments:admin_refund_management'))

        self.refund_request_service.refresh_from_db()
        self.assertEqual(self.refund_request_service.status, 'rejected')
        self.assertEqual(self.refund_request_service.rejection_reason, 'Test rejection reason')

        mock_messages_success.assert_called_once()
        self.assertEqual(mock_send_templated_email.call_count, 1) # Only admin email

        # Check admin email call
        admin_email_call = mock_send_templated_email.call_args_list[0]
        self.assertEqual(admin_email_call.kwargs['recipient_list'], [settings.DEFAULT_FROM_EMAIL])
        self.assertIn('Refund Request', admin_email_call.kwargs['subject'])

    @patch('django.contrib.messages.error')
    def test_post_reject_refund_request_invalid_form_data(self, mock_messages_error):
        url = reverse('payments:reject_refund_request', kwargs={'pk': self.refund_request_service.pk})
        form_data = {
            'rejection_reason': '', # Invalid: should be required
            'send_rejection_email': True,
        }
        response = self.client.post(url, data=form_data)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'payments/admin_reject_refund_form.html')
        self.assertIn('form', response.context)
        self.assertFalse(response.context['form'].is_valid())
        mock_messages_error.assert_called_once_with(mock.ANY, "Please correct the errors below.")

    @patch('payments.views.Refunds.admin_reject_refund_view.send_templated_email')
    @patch('django.contrib.messages.warning')
    @patch('django.contrib.messages.success')
    @patch('django.utils.timezone.now')
    def test_post_reject_refund_request_no_user_recipient_email(self, mock_now, mock_messages_success, mock_messages_warning, mock_send_templated_email):
        mock_now.return_value = timezone.now()
        # Create a refund request with no request_email and no user linked to profile
        sales_profile_no_email = SalesProfileFactory(email=None, user=None)
        sales_booking = SalesBookingFactory(sales_profile=sales_profile_no_email)
        refund_request_no_email = RefundRequestFactory(sales_booking=sales_booking, request_email=None, status='pending')

        url = reverse('payments:reject_refund_request', kwargs={'pk': refund_request_no_email.pk})
        form_data = {
            'rejection_reason': 'Test rejection reason',
            'send_rejection_email': True,
        }
        response = self.client.post(url, data=form_data)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('payments:admin_refund_management'))

        refund_request_no_email.refresh_from_db()
        self.assertEqual(refund_request_no_email.status, 'rejected')

        mock_messages_warning.assert_called_once_with(mock.ANY, "Could not send automated rejection email to user: No recipient email found.")
        self.assertEqual(mock_send_templated_email.call_count, 1) # Only admin email

        # Check admin email call
        admin_email_call = mock_send_templated_email.call_args_list[0]
        self.assertEqual(admin_email_call.kwargs['recipient_list'], [settings.DEFAULT_FROM_EMAIL])

    def test_admin_required_mixin(self):
        self.client.logout()
        url = reverse('payments:reject_refund_request', kwargs={'pk': self.refund_request_service.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('users:login') + '?next=' + url)
