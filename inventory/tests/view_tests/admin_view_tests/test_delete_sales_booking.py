from django.test import TestCase, Client
from django.urls import reverse
from django.contrib import messages
from unittest import mock

from inventory.models import SalesBooking

from ...test_helpers.model_factories import SalesBookingFactory, UserFactory

class SalesBookingDeleteViewTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        cls.admin_user = UserFactory(username='admin', email='admin@example.com', is_staff=True, is_superuser=True)
        cls.admin_user.set_password('adminpassword')
        cls.admin_user.save()

        cls.non_admin_user = UserFactory(username='user', email='user@example.com', is_staff=False, is_superuser=False)
        cls.non_admin_user.set_password('userpassword')
        cls.non_admin_user.save()

        cls.sales_booking_to_delete = SalesBookingFactory()
        cls.delete_url = reverse('inventory:admin_sales_booking_delete', kwargs={'pk': cls.sales_booking_to_delete.pk})

    def test_delete_sales_booking_as_admin_success(self):
        self.client.login(username='admin', password='adminpassword')
        self.assertTrue(SalesBooking.objects.filter(pk=self.sales_booking_to_delete.pk).exists())
        initial_count = SalesBooking.objects.count()

        response = self.client.post(self.delete_url, follow=True)

        self.assertRedirects(response, reverse('inventory:sales_bookings_management'))
        self.assertEqual(SalesBooking.objects.count(), initial_count - 1)
        self.assertFalse(SalesBooking.objects.filter(pk=self.sales_booking_to_delete.pk).exists())

        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 1)
        self.assertEqual(str(messages_list[0]), f'Sales booking {self.sales_booking_to_delete.sales_booking_reference} deleted successfully!')

    def test_delete_sales_booking_as_admin_not_found(self):
        self.client.login(username='admin', password='adminpassword')
        non_existent_pk = self.sales_booking_to_delete.pk + 999
        url = reverse('inventory:admin_sales_booking_delete', kwargs={'pk': non_existent_pk})

        response = self.client.post(url, follow=True)

        self.assertEqual(response.status_code, 404)
        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 0)

    @mock.patch('inventory.models.SalesBooking.delete')
    def test_delete_sales_booking_as_admin_failure(self, mock_sales_booking_delete):
        mock_sales_booking_delete.side_effect = Exception("DB error!")

        self.client.login(username='admin', password='adminpassword')
        response = self.client.post(self.delete_url, follow=True)

        self.assertRedirects(response, reverse('inventory:sales_bookings_management'))
        self.assertTrue(SalesBooking.objects.filter(pk=self.sales_booking_to_delete.pk).exists())

        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 1)
        self.assertIn('Error deleting sales booking', str(messages_list[0]))
        self.assertIn('DB error!', str(messages_list[0]))

    def test_delete_sales_booking_as_non_admin(self):
        self.client.login(username='user', password='userpassword')
        self.assertTrue(SalesBooking.objects.filter(pk=self.sales_booking_to_delete.pk).exists())
        initial_count = SalesBooking.objects.count()

        response = self.client.post(self.delete_url, follow=True)

        self.assertRedirects(response, f'{reverse("users:login")}?next={self.delete_url}')
        self.assertTrue(SalesBooking.objects.filter(pk=self.sales_booking_to_delete.pk).exists())
        self.assertEqual(SalesBooking.objects.count(), initial_count)

        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertGreater(len(messages_list), 0)
        self.assertIn("You do not have sufficient privileges to access this page.", str(messages_list[0]))

    def test_delete_sales_booking_unauthenticated(self):
        self.assertTrue(SalesBooking.objects.filter(pk=self.sales_booking_to_delete.pk).exists())
        initial_count = SalesBooking.objects.count()

        response = self.client.post(self.delete_url, follow=True)

        self.assertRedirects(response, f'{reverse("users:login")}?next={self.delete_url}')
        self.assertTrue(SalesBooking.objects.filter(pk=self.sales_booking_to_delete.pk).exists())
        self.assertEqual(SalesBooking.objects.count(), initial_count)

        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 0)
