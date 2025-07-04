from django.test import TestCase, Client
from django.urls import reverse
from inventory.tests.test_helpers.model_factories import (
    MotorcycleFactory,
    BlockedSalesDateFactory,
    SalesBookingFactory,
    SalesProfileFactory,
    UserFactory, 
    SalesFAQFactory, 
    FeaturedMotorcycleFactory
)

class InventoryAdminViewsRedirectTestCase(TestCase):
    """
    Tests that all inventory admin views redirect non-superuser users
    (including staff) to the login page.
    """

    def setUp(self):
        """Set up the client, users, and necessary model instances for the tests."""
        self.client = Client()
        self.login_url = reverse("users:login")

        # Create a regular user (not staff, not superuser)
        self.regular_user = UserFactory(password="password123")

        # Create a staff user (staff, but not superuser)
        self.staff_user = UserFactory(is_staff=True, password="password123")
        
        # Create a superuser for sanity checks (should not be redirected)
        self.admin_user = UserFactory(is_staff=True, is_superuser=True, password="password123")

        # Create instances of models needed for URLs with primary keys
        self.motorcycle = MotorcycleFactory()
        self.blocked_sales_date = BlockedSalesDateFactory()
        self.sales_booking = SalesBookingFactory()
        self.sales_profile = SalesProfileFactory()
        self.sales_faq = SalesFAQFactory()
        self.featured_motorcycle = FeaturedMotorcycleFactory()

    def _assert_redirects_to_login(self, url, user):
        """
        Helper method to log in a user, make a request, and assert it redirects
        to the login page.
        """
        self.client.login(username=user.username, password="password123")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302, f"URL {url} did not redirect for user {user.username}")
        self.assertIn(self.login_url, response.url, f"URL {url} redirected to {response.url} instead of login for user {user.username}")
        self.client.logout()

    # --- Tests for Regular User (Non-Staff) ---

    def test_inventory_settings_redirects_regular_user(self):
        url = reverse("inventory:inventory_settings")
        self._assert_redirects_to_login(url, self.regular_user)

    def test_admin_inventory_management_redirects_regular_user(self):
        url = reverse("inventory:admin_inventory_management")
        self._assert_redirects_to_login(url, self.regular_user)

    def test_admin_motorcycle_create_redirects_regular_user(self):
        url = reverse("inventory:admin_motorcycle_create")
        self._assert_redirects_to_login(url, self.regular_user)

    def test_admin_motorcycle_update_redirects_regular_user(self):
        url = reverse("inventory:admin_motorcycle_update", args=[self.motorcycle.pk])
        self._assert_redirects_to_login(url, self.regular_user)

    def test_admin_motorcycle_delete_redirects_regular_user(self):
        url = reverse("inventory:admin_motorcycle_delete", args=[self.motorcycle.pk])
        self._assert_redirects_to_login(url, self.regular_user)

    def test_admin_motorcycle_details_redirects_regular_user(self):
        url = reverse("inventory:admin_motorcycle_details", args=[self.motorcycle.pk])
        self._assert_redirects_to_login(url, self.regular_user)

    def test_blocked_sales_date_management_redirects_regular_user(self):
        url = reverse("inventory:blocked_sales_date_management")
        self._assert_redirects_to_login(url, self.regular_user)

    def test_blocked_sales_date_create_redirects_regular_user(self):
        url = reverse("inventory:blocked_sales_date_create")
        self._assert_redirects_to_login(url, self.regular_user)

    def test_blocked_sales_date_update_redirects_regular_user(self):
        url = reverse("inventory:blocked_sales_date_update", args=[self.blocked_sales_date.pk])
        self._assert_redirects_to_login(url, self.regular_user)

    def test_admin_blocked_sales_date_delete_redirects_regular_user(self):
        url = reverse("inventory:admin_blocked_sales_date_delete", args=[self.blocked_sales_date.pk])
        self._assert_redirects_to_login(url, self.regular_user)

    def test_sales_bookings_management_redirects_regular_user(self):
        url = reverse("inventory:sales_bookings_management")
        self._assert_redirects_to_login(url, self.regular_user)

    def test_sales_booking_create_redirects_regular_user(self):
        url = reverse("inventory:sales_booking_create")
        self._assert_redirects_to_login(url, self.regular_user)

    def test_sales_booking_update_redirects_regular_user(self):
        url = reverse("inventory:sales_booking_update", args=[self.sales_booking.pk])
        self._assert_redirects_to_login(url, self.regular_user)

    def test_admin_sales_booking_delete_redirects_regular_user(self):
        url = reverse("inventory:admin_sales_booking_delete", args=[self.sales_booking.pk])
        self._assert_redirects_to_login(url, self.regular_user)

    def test_sales_booking_details_redirects_regular_user(self):
        url = reverse("inventory:sales_booking_details", args=[self.sales_booking.pk])
        self._assert_redirects_to_login(url, self.regular_user)

    def test_admin_sales_booking_action_redirects_regular_user(self):
        url = reverse("inventory:admin_sales_booking_action", args=[self.sales_booking.pk, "confirm"])
        self._assert_redirects_to_login(url, self.regular_user)

    def test_sales_profile_management_redirects_regular_user(self):
        url = reverse("inventory:sales_profile_management")
        self._assert_redirects_to_login(url, self.regular_user)

    def test_sales_profile_create_redirects_regular_user(self):
        url = reverse("inventory:sales_profile_create")
        self._assert_redirects_to_login(url, self.regular_user)

    def test_sales_profile_update_redirects_regular_user(self):
        url = reverse("inventory:sales_profile_update", args=[self.sales_profile.pk])
        self._assert_redirects_to_login(url, self.regular_user)

    def test_admin_sales_profile_delete_redirects_regular_user(self):
        url = reverse("inventory:admin_sales_profile_delete", args=[self.sales_profile.pk])
        self._assert_redirects_to_login(url, self.regular_user)

    def test_sales_profile_details_redirects_regular_user(self):
        url = reverse("inventory:sales_profile_details", args=[self.sales_profile.pk])
        self._assert_redirects_to_login(url, self.regular_user)

    def test_sales_faq_management_redirects_regular_user(self):
        url = reverse("inventory:sales_faq_management")
        self._assert_redirects_to_login(url, self.regular_user)

    def test_sales_faq_create_redirects_regular_user(self):
        url = reverse("inventory:sales_faq_create")
        self._assert_redirects_to_login(url, self.regular_user)

    def test_sales_faq_update_redirects_regular_user(self):
        url = reverse("inventory:sales_faq_update", args=[self.sales_faq.pk])
        self._assert_redirects_to_login(url, self.regular_user)

    def test_sales_faq_delete_redirects_regular_user(self):
        url = reverse("inventory:sales_faq_delete", args=[self.sales_faq.pk])
        self._assert_redirects_to_login(url, self.regular_user)

    def test_featured_motorcycles_redirects_regular_user(self):
        url = reverse("inventory:featured_motorcycles")
        self._assert_redirects_to_login(url, self.regular_user)

    def test_add_featured_motorcycle_redirects_regular_user(self):
        url = reverse("inventory:add_featured_motorcycle")
        self._assert_redirects_to_login(url, self.regular_user)

    def test_update_featured_motorcycle_redirects_regular_user(self):
        url = reverse("inventory:update_featured_motorcycle", args=[self.featured_motorcycle.pk])
        self._assert_redirects_to_login(url, self.regular_user)

    def test_delete_featured_motorcycle_redirects_regular_user(self):
        url = reverse("inventory:delete_featured_motorcycle", args=[self.featured_motorcycle.pk])
        self._assert_redirects_to_login(url, self.regular_user)

    # --- Tests for Staff User (Non-Superuser) ---

    def test_inventory_settings_redirects_staff_user(self):
        url = reverse("inventory:inventory_settings")
        self._assert_redirects_to_login(url, self.staff_user)

    def test_admin_inventory_management_redirects_staff_user(self):
        url = reverse("inventory:admin_inventory_management")
        self._assert_redirects_to_login(url, self.staff_user)

    def test_admin_motorcycle_create_redirects_staff_user(self):
        url = reverse("inventory:admin_motorcycle_create")
        self._assert_redirects_to_login(url, self.staff_user)

    def test_admin_motorcycle_update_redirects_staff_user(self):
        url = reverse("inventory:admin_motorcycle_update", args=[self.motorcycle.pk])
        self._assert_redirects_to_login(url, self.staff_user)

    def test_admin_motorcycle_delete_redirects_staff_user(self):
        url = reverse("inventory:admin_motorcycle_delete", args=[self.motorcycle.pk])
        self._assert_redirects_to_login(url, self.staff_user)

    def test_admin_motorcycle_details_redirects_staff_user(self):
        url = reverse("inventory:admin_motorcycle_details", args=[self.motorcycle.pk])
        self._assert_redirects_to_login(url, self.staff_user)

    def test_blocked_sales_date_management_redirects_staff_user(self):
        url = reverse("inventory:blocked_sales_date_management")
        self._assert_redirects_to_login(url, self.staff_user)

    def test_blocked_sales_date_create_redirects_staff_user(self):
        url = reverse("inventory:blocked_sales_date_create")
        self._assert_redirects_to_login(url, self.staff_user)

    def test_blocked_sales_date_update_redirects_staff_user(self):
        url = reverse("inventory:blocked_sales_date_update", args=[self.blocked_sales_date.pk])
        self._assert_redirects_to_login(url, self.staff_user)

    def test_admin_blocked_sales_date_delete_redirects_staff_user(self):
        url = reverse("inventory:admin_blocked_sales_date_delete", args=[self.blocked_sales_date.pk])
        self._assert_redirects_to_login(url, self.staff_user)

    def test_sales_bookings_management_redirects_staff_user(self):
        url = reverse("inventory:sales_bookings_management")
        self._assert_redirects_to_login(url, self.staff_user)

    def test_sales_booking_create_redirects_staff_user(self):
        url = reverse("inventory:sales_booking_create")
        self._assert_redirects_to_login(url, self.staff_user)

    def test_sales_booking_update_redirects_staff_user(self):
        url = reverse("inventory:sales_booking_update", args=[self.sales_booking.pk])
        self._assert_redirects_to_login(url, self.staff_user)

    def test_admin_sales_booking_delete_redirects_staff_user(self):
        url = reverse("inventory:admin_sales_booking_delete", args=[self.sales_booking.pk])
        self._assert_redirects_to_login(url, self.staff_user)

    def test_sales_booking_details_redirects_staff_user(self):
        url = reverse("inventory:sales_booking_details", args=[self.sales_booking.pk])
        self._assert_redirects_to_login(url, self.staff_user)

    def test_admin_sales_booking_action_redirects_staff_user(self):
        url = reverse("inventory:admin_sales_booking_action", args=[self.sales_booking.pk, "confirm"])
        self._assert_redirects_to_login(url, self.staff_user)

    def test_sales_profile_management_redirects_staff_user(self):
        url = reverse("inventory:sales_profile_management")
        self._assert_redirects_to_login(url, self.staff_user)

    def test_sales_profile_create_redirects_staff_user(self):
        url = reverse("inventory:sales_profile_create")
        self._assert_redirects_to_login(url, self.staff_user)

    def test_sales_profile_update_redirects_staff_user(self):
        url = reverse("inventory:sales_profile_update", args=[self.sales_profile.pk])
        self._assert_redirects_to_login(url, self.staff_user)

    def test_admin_sales_profile_delete_redirects_staff_user(self):
        url = reverse("inventory:admin_sales_profile_delete", args=[self.sales_profile.pk])
        self._assert_redirects_to_login(url, self.staff_user)

    def test_sales_profile_details_redirects_staff_user(self):
        url = reverse("inventory:sales_profile_details", args=[self.sales_profile.pk])
        self._assert_redirects_to_login(url, self.staff_user)

    def test_sales_faq_management_redirects_staff_user(self):
        url = reverse("inventory:sales_faq_management")
        self._assert_redirects_to_login(url, self.staff_user)

    def test_sales_faq_create_redirects_staff_user(self):
        url = reverse("inventory:sales_faq_create")
        self._assert_redirects_to_login(url, self.staff_user)

    def test_sales_faq_update_redirects_staff_user(self):
        url = reverse("inventory:sales_faq_update", args=[self.sales_faq.pk])
        self._assert_redirects_to_login(url, self.staff_user)

    def test_sales_faq_delete_redirects_staff_user(self):
        url = reverse("inventory:sales_faq_delete", args=[self.sales_faq.pk])
        self._assert_redirects_to_login(url, self.staff_user)

    def test_featured_motorcycles_redirects_staff_user(self):
        url = reverse("inventory:featured_motorcycles")
        self._assert_redirects_to_login(url, self.staff_user)

    def test_add_featured_motorcycle_redirects_staff_user(self):
        url = reverse("inventory:add_featured_motorcycle")
        self._assert_redirects_to_login(url, self.staff_user)

    def test_update_featured_motorcycle_redirects_staff_user(self):
        url = reverse("inventory:update_featured_motorcycle", args=[self.featured_motorcycle.pk])
        self._assert_redirects_to_login(url, self.staff_user)

    def test_delete_featured_motorcycle_redirects_staff_user(self):
        url = reverse("inventory:delete_featured_motorcycle", args=[self.featured_motorcycle.pk])
        self._assert_redirects_to_login(url, self.staff_user)

    # --- Test for Superuser Access ---
    
    def test_superuser_can_access_admin_page(self):
        """A quick check to ensure a superuser is NOT redirected."""
        self.client.login(username=self.admin_user.username, password="password123")
        url = reverse("inventory:admin_inventory_management")
        response = self.client.get(url)
        # Superuser should get a 200 OK, not a redirect
        self.assertEqual(response.status_code, 200)
        self.client.logout()
