from django.test import TestCase, Client
from django.urls import reverse
from service.tests.test_helpers.model_factories import (
    UserFactory,
    ServiceBookingFactory,
    BlockedServiceDateFactory,
    ServiceBrandFactory,
    ServiceTypeFactory,
    ServiceFAQFactory,
    ServiceProfileFactory,
    CustomerMotorcycleFactory,
)

class AdminViewsRedirectTestCase(TestCase):
    """
    Tests that all admin views redirect non-superuser users (including staff)
    to the login page.
    """

    def setUp(self):
        """Set up the client, users, and necessary model instances for the tests."""
        self.client = Client()
        self.login_url = reverse("users:login")

        # Create a regular user (not staff, not superuser)
        self.regular_user = UserFactory(
            is_staff=False,
            is_superuser=False,
            password="password123"
        )

        # Create a staff user (staff, but not superuser)
        self.staff_user = UserFactory(
            is_staff=True,
            is_superuser=False,
            password="password123"
        )
        
        # Create a superuser for sanity checks (should not be redirected)
        self.admin_user = UserFactory(
            is_staff=True,
            is_superuser=True,
            password="password123"
        )

        # Create instances of models needed for URLs with primary keys
        self.service_booking = ServiceBookingFactory()
        self.blocked_date = BlockedServiceDateFactory()
        self.service_brand = ServiceBrandFactory()
        self.service_type = ServiceTypeFactory()
        self.service_faq = ServiceFAQFactory()
        self.service_profile = ServiceProfileFactory()
        self.customer_motorcycle = CustomerMotorcycleFactory()

    def _assert_redirects_to_login(self, url, user):
        """
        Helper method to log in a user, make a request, and assert it redirects
        to the login page.
        """
        self.client.login(username=user.username, password="password123")
        response = self.client.get(url)
        # Check for a 302 redirect status code
        self.assertEqual(response.status_code, 302)
        # Check that the redirect location is the login page
        self.assertIn(self.login_url, response.url)
        self.client.logout()

    # --- Tests for Regular User (Non-Staff) ---

    def test_service_booking_management_redirects_regular_user(self):
        url = reverse("service:service_booking_management")
        self._assert_redirects_to_login(url, self.regular_user)

    def test_admin_service_booking_detail_redirects_regular_user(self):
        url = reverse("service:admin_service_booking_detail", args=[self.service_booking.pk])
        self._assert_redirects_to_login(url, self.regular_user)

    def test_admin_create_service_booking_redirects_regular_user(self):
        url = reverse("service:admin_create_service_booking")
        self._assert_redirects_to_login(url, self.regular_user)

    def test_admin_edit_service_booking_redirects_regular_user(self):
        url = reverse("service:admin_edit_service_booking", args=[self.service_booking.pk])
        self._assert_redirects_to_login(url, self.regular_user)

    def test_admin_delete_service_booking_redirects_regular_user(self):
        url = reverse("service:admin_delete_service_booking", args=[self.service_booking.pk])
        self._assert_redirects_to_login(url, self.regular_user)

    def test_service_settings_redirects_regular_user(self):
        url = reverse("service:service_settings")
        self._assert_redirects_to_login(url, self.regular_user)

    def test_blocked_service_dates_management_redirects_regular_user(self):
        url = reverse("service:blocked_service_dates_management")
        self._assert_redirects_to_login(url, self.regular_user)

    def test_delete_blocked_service_date_redirects_regular_user(self):
        url = reverse("service:delete_blocked_service_date", args=[self.blocked_date.pk])
        self._assert_redirects_to_login(url, self.regular_user)

    def test_service_brands_management_redirects_regular_user(self):
        url = reverse("service:service_brands_management")
        self._assert_redirects_to_login(url, self.regular_user)

    def test_delete_service_brand_redirects_regular_user(self):
        url = reverse("service:delete_service_brand", args=[self.service_brand.pk])
        self._assert_redirects_to_login(url, self.regular_user)

    def test_service_types_management_redirects_regular_user(self):
        url = reverse("service:service_types_management")
        self._assert_redirects_to_login(url, self.regular_user)

    def test_add_service_type_redirects_regular_user(self):
        url = reverse("service:add_service_type")
        self._assert_redirects_to_login(url, self.regular_user)

    def test_edit_service_type_redirects_regular_user(self):
        url = reverse("service:edit_service_type", args=[self.service_type.pk])
        self._assert_redirects_to_login(url, self.regular_user)

    def test_delete_service_type_redirects_regular_user(self):
        url = reverse("service:delete_service_type", args=[self.service_type.pk])
        self._assert_redirects_to_login(url, self.regular_user)

    def test_service_faq_management_redirects_regular_user(self):
        url = reverse("service:service_faq_management")
        self._assert_redirects_to_login(url, self.regular_user)

    def test_service_faq_create_redirects_regular_user(self):
        url = reverse("service:service_faq_create")
        self._assert_redirects_to_login(url, self.regular_user)

    def test_service_faq_update_redirects_regular_user(self):
        url = reverse("service:service_faq_update", args=[self.service_faq.pk])
        self._assert_redirects_to_login(url, self.regular_user)

    def test_service_faq_delete_redirects_regular_user(self):
        url = reverse("service:service_faq_delete", args=[self.service_faq.pk])
        self._assert_redirects_to_login(url, self.regular_user)

    def test_admin_service_profiles_redirects_regular_user(self):
        url = reverse("service:admin_service_profiles")
        self._assert_redirects_to_login(url, self.regular_user)

    def test_admin_create_service_profile_redirects_regular_user(self):
        url = reverse("service:admin_create_service_profile")
        self._assert_redirects_to_login(url, self.regular_user)

    def test_admin_edit_service_profile_redirects_regular_user(self):
        url = reverse("service:admin_edit_service_profile", args=[self.service_profile.pk])
        self._assert_redirects_to_login(url, self.regular_user)

    def test_admin_delete_service_profile_redirects_regular_user(self):
        url = reverse("service:admin_delete_service_profile", args=[self.service_profile.pk])
        self._assert_redirects_to_login(url, self.regular_user)

    def test_admin_customer_motorcycle_management_redirects_regular_user(self):
        url = reverse("service:admin_customer_motorcycle_management")
        self._assert_redirects_to_login(url, self.regular_user)

    def test_admin_create_customer_motorcycle_redirects_regular_user(self):
        url = reverse("service:admin_create_customer_motorcycle")
        self._assert_redirects_to_login(url, self.regular_user)

    def test_admin_edit_customer_motorcycle_redirects_regular_user(self):
        url = reverse("service:admin_edit_customer_motorcycle", args=[self.customer_motorcycle.pk])
        self._assert_redirects_to_login(url, self.regular_user)

    def test_admin_delete_customer_motorcycle_redirects_regular_user(self):
        url = reverse("service:admin_delete_customer_motorcycle", args=[self.customer_motorcycle.pk])
        self._assert_redirects_to_login(url, self.regular_user)


    # --- Tests for Staff User (Non-Superuser) ---

    def test_service_booking_management_redirects_staff_user(self):
        url = reverse("service:service_booking_management")
        self._assert_redirects_to_login(url, self.staff_user)

    def test_admin_service_booking_detail_redirects_staff_user(self):
        url = reverse("service:admin_service_booking_detail", args=[self.service_booking.pk])
        self._assert_redirects_to_login(url, self.staff_user)

    def test_admin_create_service_booking_redirects_staff_user(self):
        url = reverse("service:admin_create_service_booking")
        self._assert_redirects_to_login(url, self.staff_user)

    def test_admin_edit_service_booking_redirects_staff_user(self):
        url = reverse("service:admin_edit_service_booking", args=[self.service_booking.pk])
        self._assert_redirects_to_login(url, self.staff_user)

    def test_admin_delete_service_booking_redirects_staff_user(self):
        url = reverse("service:admin_delete_service_booking", args=[self.service_booking.pk])
        self._assert_redirects_to_login(url, self.staff_user)

    def test_service_settings_redirects_staff_user(self):
        url = reverse("service:service_settings")
        self._assert_redirects_to_login(url, self.staff_user)

    def test_blocked_service_dates_management_redirects_staff_user(self):
        url = reverse("service:blocked_service_dates_management")
        self._assert_redirects_to_login(url, self.staff_user)

    def test_delete_blocked_service_date_redirects_staff_user(self):
        url = reverse("service:delete_blocked_service_date", args=[self.blocked_date.pk])
        self._assert_redirects_to_login(url, self.staff_user)

    def test_service_brands_management_redirects_staff_user(self):
        url = reverse("service:service_brands_management")
        self._assert_redirects_to_login(url, self.staff_user)

    def test_delete_service_brand_redirects_staff_user(self):
        url = reverse("service:delete_service_brand", args=[self.service_brand.pk])
        self._assert_redirects_to_login(url, self.staff_user)

    def test_service_types_management_redirects_staff_user(self):
        url = reverse("service:service_types_management")
        self._assert_redirects_to_login(url, self.staff_user)

    def test_add_service_type_redirects_staff_user(self):
        url = reverse("service:add_service_type")
        self._assert_redirects_to_login(url, self.staff_user)

    def test_edit_service_type_redirects_staff_user(self):
        url = reverse("service:edit_service_type", args=[self.service_type.pk])
        self._assert_redirects_to_login(url, self.staff_user)

    def test_delete_service_type_redirects_staff_user(self):
        url = reverse("service:delete_service_type", args=[self.service_type.pk])
        self._assert_redirects_to_login(url, self.staff_user)

    def test_service_faq_management_redirects_staff_user(self):
        url = reverse("service:service_faq_management")
        self._assert_redirects_to_login(url, self.staff_user)

    def test_service_faq_create_redirects_staff_user(self):
        url = reverse("service:service_faq_create")
        self._assert_redirects_to_login(url, self.staff_user)

    def test_service_faq_update_redirects_staff_user(self):
        url = reverse("service:service_faq_update", args=[self.service_faq.pk])
        self._assert_redirects_to_login(url, self.staff_user)

    def test_service_faq_delete_redirects_staff_user(self):
        url = reverse("service:service_faq_delete", args=[self.service_faq.pk])
        self._assert_redirects_to_login(url, self.staff_user)

    def test_admin_service_profiles_redirects_staff_user(self):
        url = reverse("service:admin_service_profiles")
        self._assert_redirects_to_login(url, self.staff_user)

    def test_admin_create_service_profile_redirects_staff_user(self):
        url = reverse("service:admin_create_service_profile")
        self._assert_redirects_to_login(url, self.staff_user)

    def test_admin_edit_service_profile_redirects_staff_user(self):
        url = reverse("service:admin_edit_service_profile", args=[self.service_profile.pk])
        self._assert_redirects_to_login(url, self.staff_user)

    def test_admin_delete_service_profile_redirects_staff_user(self):
        url = reverse("service:admin_delete_service_profile", args=[self.service_profile.pk])
        self._assert_redirects_to_login(url, self.staff_user)

    def test_admin_customer_motorcycle_management_redirects_staff_user(self):
        url = reverse("service:admin_customer_motorcycle_management")
        self._assert_redirects_to_login(url, self.staff_user)

    def test_admin_create_customer_motorcycle_redirects_staff_user(self):
        url = reverse("service:admin_create_customer_motorcycle")
        self._assert_redirects_to_login(url, self.staff_user)

    def test_admin_edit_customer_motorcycle_redirects_staff_user(self):
        url = reverse("service:admin_edit_customer_motorcycle", args=[self.customer_motorcycle.pk])
        self._assert_redirects_to_login(url, self.staff_user)

    def test_admin_delete_customer_motorcycle_redirects_staff_user(self):
        url = reverse("service:admin_delete_customer_motorcycle", args=[self.customer_motorcycle.pk])
        self._assert_redirects_to_login(url, self.staff_user)
        
    # --- Test for Superuser Access ---
    
    def test_superuser_can_access_admin_page(self):
        """A quick check to ensure a superuser is NOT redirected."""
        self.client.login(username=self.admin_user.username, password="password123")
        url = reverse("service:service_booking_management")
        response = self.client.get(url)
        # Superuser should get a 200 OK, not a redirect
        self.assertEqual(response.status_code, 200)
        self.client.logout()

