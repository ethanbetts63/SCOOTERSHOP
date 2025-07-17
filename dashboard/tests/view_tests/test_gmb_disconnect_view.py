from django.test import TestCase, override_settings
from django.urls import reverse
from dashboard.models import GoogleMyBusinessAccount
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


# Mock settings for GMB client ID and secret
@override_settings(
    GMB_CLIENT_ID="test_client_id",
    GMB_CLIENT_SECRET="test_client_secret",
    SITE_BASE_URL="http://testserver",
)
class GoogleMyBusinessDisconnectViewTest(TestCase):
    def setUp(self):
        GoogleMyBusinessAccount.objects.all().delete()
        self.client = self.client_class()
        self.admin_user = User.objects.create_user(
            username="admin",
            email="admin@example.com",
            password="password",
            is_staff=True,
            is_superuser=True,
        )
        self.user = User.objects.create_user(
            username="user",
            email="user@example.com",
            password="password",
            is_staff=False,
            is_superuser=False,
        )

    def test_successful_disconnection(self):
        # Configure a GMB account first
        gmb_account = GoogleMyBusinessAccount.load()
        gmb_account.account_id = "test_account"
        gmb_account.location_id = "test_location"
        gmb_account.access_token = "test_access_token"
        gmb_account.refresh_token = "test_refresh_token"
        gmb_account.token_expiry = timezone.now() + timezone.timedelta(hours=1)
        gmb_account.save()

        self.client.login(username="admin", password="password")
        response = self.client.post(reverse("dashboard:gmb_disconnect"))

        # Assertions for successful disconnection
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("dashboard:gmb_settings"))

        messages = list(response.wsgi_request._messages)
        self.assertEqual(len(messages), 1)
        self.assertEqual(
            str(messages[0]), "Successfully disconnected from Google My Business."
        )

        # Verify that credentials are cleared in the database
        gmb_account = GoogleMyBusinessAccount.load()
        self.assertIsNone(gmb_account.account_id)
        self.assertIsNone(gmb_account.location_id)
        self.assertIsNone(gmb_account.access_token)
        self.assertIsNone(gmb_account.refresh_token)
        self.assertIsNone(gmb_account.token_expiry)

    def test_unauthenticated_access_redirects_to_login(self):
        response = self.client.post(reverse("dashboard:gmb_disconnect"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("users:login"), response.url)

    def test_non_admin_access_redirects_to_login(self):
        self.client.login(username="user", password="password")
        response = self.client.post(reverse("dashboard:gmb_disconnect"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("users:login"), response.url)
