from django.test import TestCase, Client
from django.urls import reverse
from django.contrib import messages
from unittest import mock

from inventory.models import SalesProfile



from users.tests.test_helpers.model_factories import UserFactory
from inventory.tests.test_helpers.model_factories import SalesProfileFactory

class SalesProfileDeleteViewTest(TestCase):

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

        cls.sales_profile_to_delete = SalesProfileFactory(
            name="Profile To Delete", email="delete@example.com"
        )
        cls.delete_url = reverse(
            "inventory:admin_sales_profile_delete",
            kwargs={"pk": cls.sales_profile_to_delete.pk},
        )

    def test_delete_sales_profile_as_admin_success(self):
        self.client.login(username="admin", password="adminpassword")
        self.assertTrue(
            SalesProfile.objects.filter(pk=self.sales_profile_to_delete.pk).exists()
        )
        initial_count = SalesProfile.objects.count()

        response = self.client.post(self.delete_url, follow=True)

        self.assertRedirects(response, reverse("inventory:sales_profile_management"))
        self.assertEqual(SalesProfile.objects.count(), initial_count - 1)
        self.assertFalse(
            SalesProfile.objects.filter(pk=self.sales_profile_to_delete.pk).exists()
        )

        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 1)
        self.assertEqual(
            str(messages_list[0]),
            f"Sales profile for {self.sales_profile_to_delete.name} deleted successfully!",
        )

    def test_delete_sales_profile_as_admin_not_found(self):
        self.client.login(username="admin", password="adminpassword")
        non_existent_pk = self.sales_profile_to_delete.pk + 999
        url = reverse(
            "inventory:admin_sales_profile_delete", kwargs={"pk": non_existent_pk}
        )

        response = self.client.post(url, follow=True)

        self.assertEqual(response.status_code, 404)
        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 0)

    @mock.patch("inventory.models.SalesProfile.delete")
    def test_delete_sales_profile_as_admin_failure(self, mock_sales_profile_delete):
        mock_sales_profile_delete.side_effect = Exception("DB error!")

        self.client.login(username="admin", password="adminpassword")
        response = self.client.post(self.delete_url, follow=True)

        self.assertRedirects(response, reverse("inventory:sales_profile_management"))
        self.assertTrue(
            SalesProfile.objects.filter(pk=self.sales_profile_to_delete.pk).exists()
        )

        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 1)
        self.assertIn("Error deleting sales profile", str(messages_list[0]))
        self.assertIn("DB error!", str(messages_list[0]))

    def test_delete_sales_profile_as_non_admin(self):
        self.client.login(username="user", password="userpassword")
        self.assertTrue(
            SalesProfile.objects.filter(pk=self.sales_profile_to_delete.pk).exists()
        )
        initial_count = SalesProfile.objects.count()

        response = self.client.post(self.delete_url, follow=True)

        self.assertRedirects(
            response, f'{reverse("users:login")}?next={self.delete_url}'
        )
        self.assertTrue(
            SalesProfile.objects.filter(pk=self.sales_profile_to_delete.pk).exists()
        )
        self.assertEqual(SalesProfile.objects.count(), initial_count)

        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertGreater(len(messages_list), 0)
        self.assertIn(
            "You do not have sufficient privileges to access this page.",
            str(messages_list[0]),
        )

    def test_delete_sales_profile_unauthenticated(self):
        self.assertTrue(
            SalesProfile.objects.filter(pk=self.sales_profile_to_delete.pk).exists()
        )
        initial_count = SalesProfile.objects.count()

        response = self.client.post(self.delete_url, follow=True)

        self.assertRedirects(
            response, f'{reverse("users:login")}?next={self.delete_url}'
        )
        self.assertTrue(
            SalesProfile.objects.filter(pk=self.sales_profile_to_delete.pk).exists()
        )
        self.assertEqual(SalesProfile.objects.count(), initial_count)

        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 0)
