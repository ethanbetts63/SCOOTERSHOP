from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model


from users.tests.test_helpers.model_factories import UserFactory, SuperUserFactory
from inventory.tests.test_helpers.model_factories import SalesProfileFactory




class SalesProfileDetailsViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()

        cls.user = UserFactory(username="testuser", is_staff=False, is_superuser=False)
        cls.user.set_password("password123")
        cls.user.save()

        cls.admin_user = SuperUserFactory(
            username="adminuser",
        )

        cls.sales_profile = SalesProfileFactory(
            user=cls.user, name="John Doe's Profile"
        )
        cls.url = reverse(
            "inventory:sales_profile_details", kwargs={"pk": cls.sales_profile.pk}
        )

    def test_view_redirects_for_anonymous_user(self):
        response = self.client.get(self.url)
        self.assertRedirects(response, f"{reverse('users:login')}?next={self.url}")

    def test_view_redirects_for_non_admin_user(self):
        self.client.login(username="testuser", password="password123")
        response = self.client.get(self.url)
        self.assertRedirects(response, f"{reverse('users:login')}?next={self.url}")

    def test_view_accessible_for_admin_user(self):
        self.client.login(username="adminuser", password="password123")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "inventory/admin_sales_profile_details.html")

    def test_context_data(self):
        self.client.login(username="adminuser", password="password123")
        response = self.client.get(self.url)

        self.assertIn("sales_profile", response.context)
        self.assertEqual(response.context["sales_profile"], self.sales_profile)

        self.assertIn("page_title", response.context)
        self.assertEqual(
            response.context["page_title"],
            f"Sales Profile Details: {self.sales_profile.name}",
        )

    def test_404_for_non_existent_sales_profile(self):
        self.client.login(username="adminuser", password="password123")
        non_existent_url = reverse(
            "inventory:sales_profile_details", kwargs={"pk": 99999}
        )
        response = self.client.get(non_existent_url)
        self.assertEqual(response.status_code, 404)
