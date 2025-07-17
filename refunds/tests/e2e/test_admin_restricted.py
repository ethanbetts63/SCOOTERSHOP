from django.test import TestCase, Client
from django.urls import reverse
from users.tests.test_helpers.model_factories import UserFactory, StaffUserFactory, SuperUserFactory
from refunds.tests.test_helpers.model_factories import (
    RefundRequestFactory,
    RefundSettingsFactory,
)


class PaymentsAdminViewsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.login_url = reverse("users:login")
        self.regular_user = UserFactory(password="password123")
        self.staff_user = StaffUserFactory()
        self.admin_user = SuperUserFactory()
        self.refund_request = RefundRequestFactory()
        RefundSettingsFactory()

    def _assert_redirects_to_login(self, url):
        self.client.login(username=self.regular_user.username, password="password123")
        response = self.client.get(url)
        self.assertEqual(
            response.status_code, 302, f"URL {url} did not redirect for regular user."
        )
        self.assertIn(self.login_url, response.url)
        self.client.logout()

    def _assert_staff_access_allowed(self, url):
        self.client.login(username=self.staff_user.username, password="password123")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200, f"URL {url} blocked staff user.")
        self.client.logout()

    def _assert_superuser_access_allowed(self, url):
        self.client.login(username=self.admin_user.username, password="password123")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200, f"URL {url} blocked superuser.")
        self.client.logout()

    def test_admin_refund_management_permissions(self):
        url = reverse("refunds:admin_refund_management")
        self._assert_redirects_to_login(url)
        self._assert_staff_access_allowed(url)
        self._assert_superuser_access_allowed(url)

    def test_add_refund_request_permissions(self):
        url = reverse("refunds:add_refund_request")
        self._assert_redirects_to_login(url)
        self._assert_staff_access_allowed(url)
        self._assert_superuser_access_allowed(url)

    def test_edit_refund_request_permissions(self):
        url = reverse("refunds:edit_refund_request", args=[self.refund_request.pk])
        self._assert_redirects_to_login(url)
        self._assert_staff_access_allowed(url)
        self._assert_superuser_access_allowed(url)

    def test_process_refund_permissions(self):
        url = reverse("refunds:process_refund", args=[self.refund_request.pk])
        self._assert_redirects_to_login(url)
        self.client.login(username=self.staff_user.username, password="password123")
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("refunds:admin_refund_management"), response.url)
        self.client.logout()
        self.client.login(username=self.admin_user.username, password="password123")
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.client.logout()

    def test_reject_refund_request_permissions(self):
        url = reverse("refunds:reject_refund_request", args=[self.refund_request.pk])
        self._assert_redirects_to_login(url)
        self._assert_staff_access_allowed(url)
        self._assert_superuser_access_allowed(url)

    def test_admin_refund_settings_permissions(self):
        url = reverse("refunds:admin_refund_settings")
        self._assert_redirects_to_login(url)
        self._assert_staff_access_allowed(url)
        self._assert_superuser_access_allowed(url)

    def test_initiate_refund_process_permissions(self):
        url = reverse("refunds:initiate_refund_process", args=[self.refund_request.pk])
        self._assert_redirects_to_login(url)
        self._assert_staff_access_allowed(url)
        self._assert_superuser_access_allowed(url)
