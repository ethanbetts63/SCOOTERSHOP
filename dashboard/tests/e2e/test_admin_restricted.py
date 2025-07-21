from django.test import TestCase, Client
from django.urls import reverse
from users.tests.test_helpers.model_factories import UserFactory, StaffUserFactory, SuperUserFactory


class DashboardAdminViewsRedirectTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.login_url = reverse("users:login")
        self.regular_user = UserFactory(password="password123")
        self.staff_user = StaffUserFactory(password="password123")
        self.admin_user = SuperUserFactory()

    def _assert_redirects_to_login(self, url, user):
        self.client.login(username=user.username, password="password123")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(self.login_url, response.url)
        self.client.logout()

    def test_dashboard_index_redirects_regular_user(self):
        url = reverse("dashboard:dashboard_index")
        self._assert_redirects_to_login(url, self.regular_user)

    def test_settings_business_info_redirects_regular_user(self):
        url = reverse("dashboard:settings_business_info")
        self._assert_redirects_to_login(url, self.regular_user)

    def test_settings_visibility_redirects_regular_user(self):
        url = reverse("dashboard:settings_visibility")
        self._assert_redirects_to_login(url, self.regular_user)

    def test_dashboard_index_allows_staff_user(self):
        self.client.login(username=self.staff_user.username, password="password123")
        url = reverse("dashboard:dashboard_index")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.client.logout()

    def test_settings_business_info_allows_staff_user(self):
        self.client.login(username=self.staff_user.username, password="password123")
        url = reverse("dashboard:settings_business_info")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.client.logout()

    def test_settings_visibility_allows_staff_user(self):
        self.client.login(username=self.staff_user.username, password="password123")
        url = reverse("dashboard:settings_visibility")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.client.logout()

    def test_superuser_can_access_dashboard_pages(self):
        self.client.login(username=self.admin_user.username, password="password123")
        urls_to_check = [
            reverse("dashboard:dashboard_index"),
            reverse("dashboard:settings_business_info"),
            reverse("dashboard:settings_visibility"),
        ]
        for url in urls_to_check:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
        self.client.logout()
