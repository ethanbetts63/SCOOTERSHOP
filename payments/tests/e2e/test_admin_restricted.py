from django.test import TestCase, Client
from django.urls import reverse
from payments.tests.test_helpers.model_factories import (
    UserFactory,
    RefundRequestFactory,
    RefundPolicySettingsFactory,
)

class PaymentsAdminViewsTestCase(TestCase):
    """
    Tests access permissions for all admin-facing views in the payments app.
    - Regular users should be redirected.
    - Staff and Superusers should be granted access.
    """

    def setUp(self):
        """Set up the client, users, and necessary model instances for the tests."""
        self.client = Client()
        self.login_url = reverse("users:login")

        
        self.regular_user = UserFactory(password="password123")
        self.staff_user = UserFactory(is_staff=True, password="password123")
        self.admin_user = UserFactory(is_staff=True, is_superuser=True, password="password123")

        
        self.refund_request = RefundRequestFactory()
        RefundPolicySettingsFactory() 

    def _assert_redirects_to_login(self, url):
        """Helper to assert that a regular user is redirected."""
        self.client.login(username=self.regular_user.username, password="password123")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302, f"URL {url} did not redirect for regular user.")
        self.assertIn(self.login_url, response.url)
        self.client.logout()

    def _assert_staff_access_allowed(self, url):
        """Helper to assert that a staff user is allowed access."""
        self.client.login(username=self.staff_user.username, password="password123")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200, f"URL {url} blocked staff user.")
        self.client.logout()

    def _assert_superuser_access_allowed(self, url):
        """Helper to assert that a superuser is allowed access."""
        self.client.login(username=self.admin_user.username, password="password123")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200, f"URL {url} blocked superuser.")
        self.client.logout()

    

    def test_admin_refund_management_permissions(self):
        url = reverse("payments:admin_refund_management")
        self._assert_redirects_to_login(url)
        self._assert_staff_access_allowed(url)
        self._assert_superuser_access_allowed(url)

    def test_add_refund_request_permissions(self):
        url = reverse("payments:add_refund_request")
        self._assert_redirects_to_login(url)
        self._assert_staff_access_allowed(url)
        self._assert_superuser_access_allowed(url)

    def test_edit_refund_request_permissions(self):
        url = reverse("payments:edit_refund_request", args=[self.refund_request.pk])
        self._assert_redirects_to_login(url)
        self._assert_staff_access_allowed(url)
        self._assert_superuser_access_allowed(url)

    def test_process_refund_permissions(self):
        url = reverse("payments:process_refund", args=[self.refund_request.pk])
        self._assert_redirects_to_login(url) 
        self.client.login(username=self.staff_user.username, password="password123")
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("payments:admin_refund_management"), response.url)
        self.client.logout()
        self.client.login(username=self.admin_user.username, password="password123")
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.client.logout()

    def test_reject_refund_request_permissions(self):
        url = reverse("payments:reject_refund_request", args=[self.refund_request.pk])
        self._assert_redirects_to_login(url)
        self._assert_staff_access_allowed(url)
        self._assert_superuser_access_allowed(url)

    def test_admin_refund_settings_permissions(self):
        url = reverse("payments:admin_refund_settings")
        self._assert_redirects_to_login(url)
        self._assert_staff_access_allowed(url)
        self._assert_superuser_access_allowed(url)

    def test_initiate_refund_process_permissions(self):
        url = reverse("payments:initiate_refund_process", args=[self.refund_request.pk])
        self._assert_redirects_to_login(url)
        self._assert_staff_access_allowed(url)
        self._assert_superuser_access_allowed(url)

