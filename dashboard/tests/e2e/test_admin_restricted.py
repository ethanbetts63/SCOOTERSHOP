from django.test import TestCase, Client
from django.urls import reverse

# Import factories from the dashboard app's test helpers
from dashboard.tests.test_helpers.model_factories import UserFactory, StaffUserFactory

class DashboardAdminViewsRedirectTestCase(TestCase):
    """
    Tests that all dashboard admin views redirect non-superuser users
    (including staff) to the login page.
    """

    def setUp(self):
        """Set up the client and users for the tests."""
        self.client = Client()
        self.login_url = reverse("users:login")

        # Create a regular user (not staff, not superuser)
        self.regular_user = UserFactory(password="password123")

        # Create a staff user (staff, but not superuser)
        self.staff_user = StaffUserFactory(password="password123")
        
        # Create a superuser for sanity checks (should not be redirected)
        self.admin_user = StaffUserFactory(
            is_superuser=True,
            password="password123"
        )

    def _assert_redirects_to_login(self, url, user):
        """
        Helper method to log in a user, make a request, and assert it redirects
        to the login page.
        """
        self.client.login(username=user.username, password="password123")
        response = self.client.get(url)
        # Check for a 302 redirect status code
        self.assertEqual(response.status_code, 302, f"URL {url} did not redirect for user {user.username}")
        # Check that the redirect location is the login page
        self.assertIn(self.login_url, response.url, f"URL {url} redirected to {response.url} instead of login for user {user.username}")
        self.client.logout()

    # --- Tests for Regular User (Non-Staff) ---

    def test_dashboard_index_redirects_regular_user(self):
        url = reverse("dashboard:dashboard_index")
        self._assert_redirects_to_login(url, self.regular_user)

    def test_settings_business_info_redirects_regular_user(self):
        url = reverse("dashboard:settings_business_info")
        self._assert_redirects_to_login(url, self.regular_user)

    def test_settings_visibility_redirects_regular_user(self):
        url = reverse("dashboard:settings_visibility")
        self._assert_redirects_to_login(url, self.regular_user)

    # --- Tests for Staff User (Non-Superuser) ---

    def test_dashboard_index_redirects_staff_user(self):
        url = reverse("dashboard:dashboard_index")
        self._assert_redirects_to_login(url, self.staff_user)

    def test_settings_business_info_redirects_staff_user(self):
        url = reverse("dashboard:settings_business_info")
        self._assert_redirects_to_login(url, self.staff_user)

    def test_settings_visibility_redirects_staff_user(self):
        url = reverse("dashboard:settings_visibility")
        self._assert_redirects_to_login(url, self.staff_user)

    # --- Test for Superuser Access ---
    
    def test_superuser_can_access_dashboard_pages(self):
        """A quick check to ensure a superuser is NOT redirected."""
        self.client.login(username=self.admin_user.username, password="password123")
        
        # Test all dashboard URLs for superuser access
        urls_to_check = [
            reverse("dashboard:dashboard_index"),
            reverse("dashboard:settings_business_info"),
            reverse("dashboard:settings_visibility"),
        ]

        for url in urls_to_check:
            with self.subTest(url=url):
                response = self.client.get(url)
                # Superuser should get a 200 OK, not a redirect
                self.assertEqual(response.status_code, 200, f"Superuser was redirected from {url}")

        self.client.logout()
