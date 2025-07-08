from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.contrib.messages import get_messages
from unittest.mock import patch
from inventory.models import SalesBooking
from users.models import User
from inventory.tests.test_helpers.model_factories import SalesBookingFactory, UserFactory

class SalesBookingActionViewTest(TestCase):
    def setUp(self):
        self.admin_user = UserFactory(is_staff=True)
        self.client.force_login(self.admin_user)
        self.sales_booking = SalesBookingFactory()

    def test_get_confirm_action(self):
        response = self.client.get(reverse('inventory:admin_sales_booking_action', kwargs={'pk': self.sales_booking.pk, 'action_type': 'confirm'}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'inventory/admin_sales_booking_action.html')
        self.assertEqual(response.context['action_type'], 'confirm')
        self.assertIn('form', response.context)

    def test_get_reject_action(self):
        response = self.client.get(reverse('inventory:admin_sales_booking_action', kwargs={'pk': self.sales_booking.pk, 'action_type': 'reject'}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'inventory/admin_sales_booking_action.html')
        self.assertEqual(response.context['action_type'], 'reject')
        self.assertIn('form', response.context)

    def test_dispatch_invalid_action(self):
        response = self.client.get(reverse('inventory:admin_sales_booking_action', kwargs={'pk': self.sales_booking.pk, 'action_type': 'invalid'}))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('inventory:sales_bookings_management'))

    def test_dispatch_nonexistent_booking(self):
        response = self.client.get(reverse('inventory:admin_sales_booking_action', kwargs={'pk': 999, 'action_type': 'confirm'}))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('inventory:sales_bookings_management'))

    @patch('inventory.views.admin_views.sales_booking_action_view.confirm_sales_booking')
    def test_post_confirm_action_success(self, mock_confirm):
        mock_confirm.return_value = {'success': True, 'message': 'Booking confirmed.'}
        form_data = {
            'sales_booking_id': self.sales_booking.pk,
            'action': 'confirm',
            'send_notification': True,
            'message': 'Test confirmation message'
        }
        response = self.client.post(reverse('inventory:admin_sales_booking_action', kwargs={'pk': self.sales_booking.pk, 'action_type': 'confirm'}), data=form_data)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('inventory:sales_bookings_management'))
        mock_confirm.assert_called_once()
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), 'Booking confirmed.')

    @patch('inventory.views.admin_views.sales_booking_action_view.reject_sales_booking')
    def test_post_reject_action_success(self, mock_reject):
        mock_reject.return_value = {'success': True, 'message': 'Booking rejected.'}
        form_data = {
            'sales_booking_id': self.sales_booking.pk,
            'action': 'reject',
            'send_notification': False,
            'message': 'Test rejection message'
        }
        response = self.client.post(reverse('inventory:admin_sales_booking_action', kwargs={'pk': self.sales_booking.pk, 'action_type': 'reject'}), data=form_data)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('inventory:sales_bookings_management'))
        mock_reject.assert_called_once()
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), 'Booking rejected.')