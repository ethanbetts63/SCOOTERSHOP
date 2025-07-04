from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
import factory

from ..test_helpers.model_factories import (
    UserFactory,
    MotorcycleFactory,
    SalesBookingFactory,
    SalesProfileFactory,
    BlockedSalesDateFactory,
    SalesFAQFactory,
    FeaturedMotorcycleFactory,
    InventorySettingsFactory,
    MotorcycleConditionFactory,
    StaffUserFactory,
)

User = get_user_model()

class InventoryAdminViewsPermissionsTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        cls.login_url = reverse("users:login")
        
        cls.regular_user = UserFactory(password="password123")
        cls.staff_user = StaffUserFactory()

        cls.motorcycle_condition = MotorcycleConditionFactory(name="used")
        cls.motorcycle = MotorcycleFactory(conditions=["used"])
        cls.sales_profile = SalesProfileFactory()
        cls.sales_booking = SalesBookingFactory()
        cls.blocked_date = BlockedSalesDateFactory()
        cls.faq = SalesFAQFactory()
        cls.featured_motorcycle = FeaturedMotorcycleFactory()
        InventorySettingsFactory()

    def _test_url_permissions(self, url_name, kwargs=None, method='get', data=None):
        url = reverse(url_name, kwargs=kwargs)
        
        # Test anonymous user
        response_anon = self.client.get(url)
        self.assertEqual(response_anon.status_code, 302)
        self.assertIn(self.login_url, response_anon.url)

        # Test regular user
        self.client.login(username=self.regular_user.username, password="password123")
        response_regular = self.client.get(url)
        self.assertEqual(response_regular.status_code, 302)
        self.assertIn(self.login_url, response_regular.url)
        self.client.logout()

        # Test staff user
        self.client.login(username=self.staff_user.username, password="password123")
        if method == 'post':
            response_staff = self.client.post(url, data if data else {})
        else:
            response_staff = self.client.get(url)
        
        # For POST requests that redirect on success, 302 is OK. Otherwise, expect 200.
        expected_staff_status = 302 if method == 'post' else 200
        self.assertIn(response_staff.status_code, [200, 302])
        if method == 'get':
            self.assertEqual(response_staff.status_code, 200)

        self.client.logout()

    def test_inventory_settings_permissions(self):
        self._test_url_permissions("inventory:inventory_settings")

    def test_inventory_management_permissions(self):
        self._test_url_permissions("inventory:admin_inventory_management")
        self._test_url_permissions("inventory:admin_new_motorcycle_management")
        self._test_url_permissions("inventory:admin_used_motorcycle_management")

    def test_motorcycle_crud_permissions(self):
        self._test_url_permissions("inventory:admin_motorcycle_create")
        self._test_url_permissions("inventory:admin_motorcycle_update", kwargs={'pk': self.motorcycle.pk})
        self._test_url_permissions("inventory:admin_motorcycle_delete", kwargs={'pk': self.motorcycle.pk})
        self._test_url_permissions("inventory:admin_motorcycle_details", kwargs={'pk': self.motorcycle.pk})

    def test_blocked_sales_date_crud_permissions(self):
        self._test_url_permissions("inventory:blocked_sales_date_management")
        self._test_url_permissions("inventory:blocked_sales_date_create")
        self._test_url_permissions("inventory:blocked_sales_date_update", kwargs={'pk': self.blocked_date.pk})
        self._test_url_permissions("inventory:admin_blocked_sales_date_delete", kwargs={'pk': self.blocked_date.pk})

    def test_sales_booking_crud_permissions(self):
        self._test_url_permissions("inventory:sales_bookings_management")
        self._test_url_permissions("inventory:sales_booking_create")
        self._test_url_permissions("inventory:sales_booking_update", kwargs={'pk': self.sales_booking.pk})
        self._test_url_permissions("inventory:admin_sales_booking_delete", kwargs={'pk': self.sales_booking.pk})
        self._test_url_permissions("inventory:sales_booking_details", kwargs={'pk': self.sales_booking.pk})
        self._test_url_permissions("inventory:admin_sales_booking_action", kwargs={'pk': self.sales_booking.pk, 'action_type': 'confirm'})

    def test_sales_profile_crud_permissions(self):
        self._test_url_permissions("inventory:sales_profile_management")
        self._test_url_permissions("inventory:sales_profile_create")
        self._test_url_permissions("inventory:sales_profile_update", kwargs={'pk': self.sales_profile.pk})
        self._test_url_permissions("inventory:admin_sales_profile_delete", kwargs={'pk': self.sales_profile.pk})
        self._test_url_permissions("inventory:sales_profile_details", kwargs={'pk': self.sales_profile.pk})

    def test_sales_faq_crud_permissions(self):
        self._test_url_permissions("inventory:sales_faq_management")
        self._test_url_permissions("inventory:sales_faq_create")
        self._test_url_permissions("inventory:sales_faq_update", kwargs={'pk': self.faq.pk})
        self._test_url_permissions("inventory:sales_faq_delete", kwargs={'pk': self.faq.pk})

    def test_featured_motorcycle_crud_permissions(self):
        self._test_url_permissions("inventory:featured_motorcycles")
        self._test_url_permissions("inventory:add_featured_motorcycle")
        self._test_url_permissions("inventory:update_featured_motorcycle", kwargs={'pk': self.featured_motorcycle.pk})
        self._test_url_permissions("inventory:delete_featured_motorcycle", kwargs={'pk': self.featured_motorcycle.pk})
