from django.test import TestCase, Client
from django.urls import reverse
from django.contrib import messages
from unittest import mock
from inventory.models import BlockedSalesDate
from users.tests.test_helpers.model_factories import UserFactory, SuperUserFactory
from inventory.tests.test_helpers.model_factories import BlockedSalesDateFactory

class BlockedSalesDateDeleteViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        cls.admin_user = SuperUserFactory(
            username="admin",
            email="admin@example.com",
        )

        cls.non_admin_user = UserFactory(
            username="user",
            email="user@example.com",
            is_staff=False,
            is_superuser=False,
        )
        cls.non_admin_user.set_password("userpassword")
        cls.non_admin_user.save()

        cls.blocked_date_to_delete = BlockedSalesDateFactory(
            description="Holiday Period"
        )
        cls.delete_url = reverse(
            "inventory:admin_blocked_sales_date_delete",
            kwargs={"pk": cls.blocked_date_to_delete.pk},
        )

    def test_delete_blocked_sales_date_as_admin_success(self):
        self.client.login(username="admin", password="password123")
        self.assertTrue(
            BlockedSalesDate.objects.filter(pk=self.blocked_date_to_delete.pk).exists()
        )
        initial_count = BlockedSalesDate.objects.count()

        response = self.client.post(self.delete_url, follow=True)

        self.assertRedirects(
            response, reverse("inventory:blocked_sales_date_management")
        )
        self.assertEqual(BlockedSalesDate.objects.count(), initial_count - 1)
        self.assertFalse(
            BlockedSalesDate.objects.filter(pk=self.blocked_date_to_delete.pk).exists()
        )

        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 1)
        self.assertEqual(
            str(messages_list[0]),
            f"Blocked sales date {self.blocked_date_to_delete} deleted successfully!",
        )

    def test_delete_blocked_sales_date_as_admin_not_found(self):
        self.client.login(username="admin", password="password123")
        non_existent_pk = self.blocked_date_to_delete.pk + 999
        url = reverse(
            "inventory:admin_blocked_sales_date_delete", kwargs={"pk": non_existent_pk}
        )

        response = self.client.post(url, follow=True)

        self.assertEqual(response.status_code, 404)
        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 0)

    @mock.patch("inventory.models.BlockedSalesDate.delete")
    def test_delete_blocked_sales_date_as_admin_failure(self, mock_blocked_date_delete):
        mock_blocked_date_delete.side_effect = Exception("DB error!")

        self.client.login(username="admin", password="password123")
        response = self.client.post(self.delete_url, follow=True)

        self.assertRedirects(
            response, reverse("inventory:blocked_sales_date_management")
        )
        self.assertTrue(
            BlockedSalesDate.objects.filter(pk=self.blocked_date_to_delete.pk).exists()
        )

        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 1)
        self.assertIn("Error deleting blocked sales date", str(messages_list[0]))
        self.assertIn("DB error!", str(messages_list[0]))

    def test_delete_blocked_sales_date_as_non_admin(self):
        self.client.login(username="user", password="userpassword")
        self.assertTrue(
            BlockedSalesDate.objects.filter(pk=self.blocked_date_to_delete.pk).exists()
        )
        initial_count = BlockedSalesDate.objects.count()

        response = self.client.post(self.delete_url, follow=True)

        self.assertRedirects(
            response, f"{reverse('users:login')}?next={self.delete_url}"
        )
        self.assertTrue(
            BlockedSalesDate.objects.filter(pk=self.blocked_date_to_delete.pk).exists()
        )
        self.assertEqual(BlockedSalesDate.objects.count(), initial_count)

        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertGreater(len(messages_list), 0)
        self.assertIn(
            "You do not have sufficient privileges to access this page.",
            str(messages_list[0]),
        )

    def test_delete_blocked_sales_date_unauthenticated(self):
        self.assertTrue(
            BlockedSalesDate.objects.filter(pk=self.blocked_date_to_delete.pk).exists()
        )
        initial_count = BlockedSalesDate.objects.count()

        response = self.client.post(self.delete_url, follow=True)

        self.assertRedirects(
            response, f"{reverse('users:login')}?next={self.delete_url}"
        )
        self.assertTrue(
            BlockedSalesDate.objects.filter(pk=self.blocked_date_to_delete.pk).exists()
        )
        self.assertEqual(BlockedSalesDate.objects.count(), initial_count)

        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 0)
