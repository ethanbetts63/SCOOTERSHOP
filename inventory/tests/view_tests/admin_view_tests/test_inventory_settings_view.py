import datetime
from django.test import TestCase, Client
from django.urls import reverse
from inventory.models import InventorySettings
from users.tests.test_helpers.model_factories import UserFactory, SuperUserFactory
from inventory.tests.test_helpers.model_factories import InventorySettingsFactory

class InventorySettingsViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        cls.url = reverse("inventory:inventory_settings")
        cls.user = UserFactory(username="testuser", is_staff=False, is_superuser=False)
        cls.user.set_password("password123")
        cls.user.save()
        cls.admin_user = SuperUserFactory(
            username="adminuser",
        )
        cls.settings = InventorySettingsFactory(
            deposit_amount=150.00,
            require_drivers_license=False,
            sales_appointment_start_time=datetime.time(9, 0),
            sales_appointment_end_time=datetime.time(17, 0),
        )

    def test_view_redirects_for_anonymous_user(self):
        response = self.client.get(self.url)
        self.assertRedirects(response, f"{reverse('users:login')}?next={self.url}")

    def test_view_redirects_for_non_admin_user(self):
        self.client.login(username="testuser", password="password123")
        response = self.client.get(self.url)
        self.assertRedirects(response, f"{reverse('users:login')}?next={self.url}")

    def test_get_view_as_admin(self):
        self.client.login(username="adminuser", password="password123")
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "inventory/admin_inventory_settings.html")
        self.assertIn("form", response.context)
        self.assertEqual(response.context["form"].instance, self.settings)

    def test_get_view_creates_settings_if_not_exist(self):
        InventorySettings.objects.all().delete()
        self.assertEqual(InventorySettings.objects.count(), 0)

        self.client.login(username="adminuser", password="password123")
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(InventorySettings.objects.count(), 1)
        self.assertIsInstance(response.context["form"].instance, InventorySettings)
