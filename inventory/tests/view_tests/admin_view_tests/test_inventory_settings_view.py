# inventory/tests/admin_views/test_inventory_settings_view.py

import datetime
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages

from inventory.models import InventorySettings
from ...test_helpers.model_factories import UserFactory, InventorySettingsFactory

User = get_user_model()

class InventorySettingsViewTest(TestCase):
    """
    Tests for the InventorySettingsView.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up non-modified objects used by all test methods.
        """
        cls.client = Client()
        cls.url = reverse('inventory:inventory_settings')

        # Create a non-admin user
        cls.user = UserFactory(username='testuser', is_staff=False, is_superuser=False)
        cls.user.set_password('password123')
        cls.user.save()

        # Create an admin user
        cls.admin_user = UserFactory(username='adminuser', is_staff=True, is_superuser=True)
        cls.admin_user.set_password('adminpass123')
        cls.admin_user.save()

        # Ensure the singleton settings object exists
        cls.settings = InventorySettingsFactory(
            deposit_amount=150.00,
            require_drivers_license=False,
            sales_appointment_start_time=datetime.time(9, 0),
            sales_appointment_end_time=datetime.time(17, 0)
        )

    # --- Permission Tests ---

    def test_view_redirects_for_anonymous_user(self):
        """
        Test that an unauthenticated user is redirected to the login page.
        """
        response = self.client.get(self.url)
        self.assertRedirects(response, f'{reverse("users:login")}?next={self.url}')

    def test_view_redirects_for_non_admin_user(self):
        """
        Test that a logged-in, non-admin user is redirected.
        """
        self.client.login(username='testuser', password='password123')
        response = self.client.get(self.url)
        self.assertRedirects(response, f'{reverse("users:login")}?next={self.url}')

    # --- GET Request Tests ---

    def test_get_view_as_admin(self):
        """
        Test that an admin user can access the settings page.
        """
        self.client.login(username='adminuser', password='adminpass123')
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'inventory/admin_inventory_settings.html')
        self.assertIn('form', response.context)
        self.assertEqual(response.context['form'].instance, self.settings)

    def test_get_view_creates_settings_if_not_exist(self):
        """
        Test that the view creates a settings object if it's missing.
        """
        InventorySettings.objects.all().delete()
        self.assertEqual(InventorySettings.objects.count(), 0)
        
        self.client.login(username='adminuser', password='adminpass123')
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(InventorySettings.objects.count(), 1)
        self.assertIsInstance(response.context['form'].instance, InventorySettings)

    # --- POST Request Tests ---

    def test_post_update_success(self):
        """
        Test a successful update of the inventory settings.
        """
        self.client.login(username='adminuser', password='adminpass123')
        
        post_data = {
            'deposit_amount': '250.50',
            'deposit_lifespan_days': 7,
            'require_drivers_license': 'on', # Checkbox data
            'sales_appointment_start_time': '10:00',
            'sales_appointment_end_time': '18:00',
            'sales_booking_open_days': 'Mon,Tue,Wed,Thu,Fri',
            'inventory_settings_submit': '' # Must be present to trigger view logic
        }
        
        response = self.client.post(self.url, data=post_data, follow=True)
        
        self.assertRedirects(response, self.url)
        
        self.settings.refresh_from_db()
        self.assertEqual(self.settings.deposit_amount, 250.50)
        self.assertTrue(self.settings.require_drivers_license)
        self.assertEqual(self.settings.sales_appointment_start_time, datetime.time(10, 0))

        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Inventory settings updated successfully!")


    def test_post_without_submit_button_name_is_ignored(self):
        """
        Test that a POST request without the correct submit button name is ignored by the custom logic.
        """
        self.client.login(username='adminuser', password='adminpass123')
        
        original_deposit_amount = self.settings.deposit_amount

        # Data is valid, but the submit button name is missing
        post_data = {
            'deposit_amount': '500.00',
        }

        # This post should not trigger the `if 'inventory_settings_submit' in request.POST:` block.
        # The base `UpdateView.post` might process it, but the custom success/error messaging logic will not run.
        # Given the view's current structure, it will likely not save.
        response = self.client.post(self.url, data=post_data, follow=True)
        
        self.settings.refresh_from_db()
        self.assertEqual(self.settings.deposit_amount, original_deposit_amount)

        # No success or error message should be generated from the custom logic
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 0)
