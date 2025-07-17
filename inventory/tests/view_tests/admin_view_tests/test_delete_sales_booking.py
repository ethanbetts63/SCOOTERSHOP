from django.test import TestCase, Client
from django.urls import reverse
from django.contrib import messages
from unittest import mock

from inventory.models import SalesBooking


from users.tests.test_helpers.model_factories import UserFactory
from inventory.tests.test_helpers.model_factories import SalesBookingFactory, MotorcycleFactory



class SalesBookingDeleteViewTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        cls.admin_user = UserFactory(
            username="admin",
            email="admin@example.com",
            is_staff=True,
            is_superuser=True,
        )
        cls.admin_user.set_password("adminpassword")
        cls.admin_user.save()

        cls.non_admin_user = UserFactory(
            username="user",
            email="user@example.com",
            is_staff=False,
            is_superuser=False,
        )
        cls.non_admin_user.set_password("userpassword")
        cls.non_admin_user.save()

    def setUp(self):

        self.client.login(username="admin", password="adminpassword")

    def test_delete_booking_sets_reserved_motorcycle_to_for_sale(self):

        reserved_motorcycle = MotorcycleFactory(status="reserved", is_available=False)
        sales_booking = SalesBookingFactory(motorcycle=reserved_motorcycle)
        delete_url = reverse(
            "inventory:admin_sales_booking_delete", kwargs={"pk": sales_booking.pk}
        )

        self.assertEqual(reserved_motorcycle.status, "reserved")
        initial_count = SalesBooking.objects.count()

        response = self.client.post(delete_url, follow=True)

        self.assertRedirects(response, reverse("inventory:sales_bookings_management"))
        self.assertEqual(SalesBooking.objects.count(), initial_count - 1)
        self.assertFalse(SalesBooking.objects.filter(pk=sales_booking.pk).exists())

        reserved_motorcycle.refresh_from_db()
        self.assertEqual(reserved_motorcycle.status, "for_sale")
        self.assertTrue(reserved_motorcycle.is_available)

        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 1)
        expected_message = f'Sales booking {sales_booking.sales_booking_reference} deleted and motorcycle "{reserved_motorcycle}" is now available for sale.'
        self.assertEqual(str(messages_list[0]), expected_message)

    def test_delete_booking_for_non_reserved_motorcycle(self):

        available_motorcycle = MotorcycleFactory(status="for_sale")
        sales_booking = SalesBookingFactory(motorcycle=available_motorcycle)
        delete_url = reverse(
            "inventory:admin_sales_booking_delete", kwargs={"pk": sales_booking.pk}
        )

        initial_count = SalesBooking.objects.count()

        response = self.client.post(delete_url, follow=True)

        self.assertRedirects(response, reverse("inventory:sales_bookings_management"))
        self.assertEqual(SalesBooking.objects.count(), initial_count - 1)
        self.assertFalse(SalesBooking.objects.filter(pk=sales_booking.pk).exists())

        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 1)
        expected_message = f"Sales booking {sales_booking.sales_booking_reference} deleted successfully!"
        self.assertEqual(str(messages_list[0]), expected_message)

    def test_delete_sales_booking_as_admin_not_found(self):
        non_existent_pk = 9999
        url = reverse(
            "inventory:admin_sales_booking_delete", kwargs={"pk": non_existent_pk}
        )
        response = self.client.post(url, follow=True)
        self.assertEqual(response.status_code, 404)

    @mock.patch("inventory.models.SalesBooking.delete")
    def test_delete_sales_booking_as_admin_failure(self, mock_sales_booking_delete):
        mock_sales_booking_delete.side_effect = Exception("DB error!")
        sales_booking = SalesBookingFactory()
        delete_url = reverse(
            "inventory:admin_sales_booking_delete", kwargs={"pk": sales_booking.pk}
        )

        response = self.client.post(delete_url, follow=True)

        self.assertRedirects(response, reverse("inventory:sales_bookings_management"))
        self.assertTrue(SalesBooking.objects.filter(pk=sales_booking.pk).exists())

        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 1)
        self.assertIn("Error deleting sales booking", str(messages_list[0]))
        self.assertIn("DB error!", str(messages_list[0]))

    def test_delete_sales_booking_as_non_admin(self):
        self.client.logout()
        self.client.login(username="user", password="userpassword")

        sales_booking = SalesBookingFactory()
        delete_url = reverse(
            "inventory:admin_sales_booking_delete", kwargs={"pk": sales_booking.pk}
        )
        initial_count = SalesBooking.objects.count()

        response = self.client.post(delete_url, follow=True)

        self.assertRedirects(response, f'{reverse("users:login")}?next={delete_url}')
        self.assertEqual(SalesBooking.objects.count(), initial_count)

    def test_delete_sales_booking_unauthenticated(self):
        self.client.logout()

        sales_booking = SalesBookingFactory()
        delete_url = reverse(
            "inventory:admin_sales_booking_delete", kwargs={"pk": sales_booking.pk}
        )
        initial_count = SalesBooking.objects.count()

        response = self.client.post(delete_url, follow=True)

        self.assertRedirects(response, f'{reverse("users:login")}?next={delete_url}')
        self.assertEqual(SalesBooking.objects.count(), initial_count)
