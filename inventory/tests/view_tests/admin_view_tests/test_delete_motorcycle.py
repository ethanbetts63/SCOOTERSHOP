from django.test import TestCase, Client
from django.urls import reverse
from django.contrib import messages
from unittest import mock

from inventory.models import Motorcycle



from inventory.forms.admin_motorcycle_form import MotorcycleForm
from users.tests.test_helpers.model_factories import UserFactory, StaffUserFactory
from service.tests.test_helpers.model_factories import ServiceBookingFactory, ServiceProfileFactory, ServiceTypeFactory, ServiceSettingsFactory, ServiceTermsFactory, ServicefaqFactory, CustomerMotorcycleFactory, BlockedServiceDateFactory, ServiceBrandFactory
from inventory.tests.test_helpers.model_factories import SalesBookingFactory, TempSalesBookingFactory, SalesProfileFactory, MotorcycleConditionFactory, MotorcycleFactory, MotorcycleImageFactory, FeaturedMotorcycleFactory, InventorySettingsFactory, BlockedSalesDateFactory
from payments.tests.test_helpers.model_factories import PaymentFactory, WebhookEventFactory
from refunds.tests.test_helpers.model_factories import RefundRequestFactory, RefundSettingsFactory


class MotorcycleDeleteViewTest(TestCase):

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

        cls.motorcycle_to_delete = MotorcycleFactory(
            title="Test Motorcycle Delete", stock_number="DEL001"
        )
        cls.delete_url = reverse(
            "inventory:admin_motorcycle_delete",
            kwargs={"pk": cls.motorcycle_to_delete.pk},
        )

    def test_delete_motorcycle_as_admin_success(self):
        self.client.login(username="admin", password="adminpassword")

        self.assertTrue(
            Motorcycle.objects.filter(pk=self.motorcycle_to_delete.pk).exists()
        )
        initial_motorcycle_count = Motorcycle.objects.count()

        response = self.client.post(self.delete_url, follow=True)

        self.assertRedirects(response, reverse("inventory:admin_inventory_management"))

        self.assertEqual(Motorcycle.objects.count(), initial_motorcycle_count - 1)

        self.assertFalse(
            Motorcycle.objects.filter(pk=self.motorcycle_to_delete.pk).exists()
        )

        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 1)
        self.assertEqual(
            str(messages_list[0]),
            f'Motorcycle "{self.motorcycle_to_delete.title}" deleted successfully!',
        )

    def test_delete_motorcycle_as_admin_not_found(self):
        self.client.login(username="admin", password="adminpassword")
        non_existent_pk = self.motorcycle_to_delete.pk + 999
        url = reverse(
            "inventory:admin_motorcycle_delete", kwargs={"pk": non_existent_pk}
        )

        response = self.client.post(url, follow=True)

        self.assertEqual(response.status_code, 404)
        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 0)

    @mock.patch("inventory.models.Motorcycle.delete")
    def test_delete_motorcycle_as_admin_failure(self, mock_motorcycle_delete):
        mock_motorcycle_delete.side_effect = Exception("Database error occurred!")

        self.client.login(username="admin", password="adminpassword")

        response = self.client.post(self.delete_url, follow=True)

        self.assertRedirects(response, reverse("inventory:admin_inventory_management"))

        self.assertTrue(
            Motorcycle.objects.filter(pk=self.motorcycle_to_delete.pk).exists()
        )

        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 1)
        self.assertIn("Error deleting motorcycle", str(messages_list[0]))
        self.assertIn("Database error occurred!", str(messages_list[0]))

    def test_delete_motorcycle_as_non_admin(self):
        self.client.login(username="user", password="userpassword")

        self.assertTrue(
            Motorcycle.objects.filter(pk=self.motorcycle_to_delete.pk).exists()
        )
        initial_motorcycle_count = Motorcycle.objects.count()

        response = self.client.post(self.delete_url, follow=True)

        self.assertRedirects(
            response, f'{reverse("users:login")}?next={self.delete_url}'
        )

        self.assertTrue(
            Motorcycle.objects.filter(pk=self.motorcycle_to_delete.pk).exists()
        )
        self.assertEqual(Motorcycle.objects.count(), initial_motorcycle_count)

        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertGreater(len(messages_list), 0)
        self.assertIn(
            "You do not have sufficient privileges to access this page.",
            str(messages_list[0]),
        )

    def test_delete_motorcycle_unauthenticated(self):
        self.assertTrue(
            Motorcycle.objects.filter(pk=self.motorcycle_to_delete.pk).exists()
        )
        initial_motorcycle_count = Motorcycle.objects.count()

        response = self.client.post(self.delete_url, follow=True)

        self.assertRedirects(
            response, f'{reverse("users:login")}?next={self.delete_url}'
        )

        self.assertTrue(
            Motorcycle.objects.filter(pk=self.motorcycle_to_delete.pk).exists()
        )
        self.assertEqual(Motorcycle.objects.count(), initial_motorcycle_count)

        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 0)
