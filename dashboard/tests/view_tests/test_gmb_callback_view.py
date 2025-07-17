from django.test import TestCase, override_settings
from django.urls import reverse
from unittest import mock
from dashboard.models import GoogleMyBusinessAccount
from django.contrib.auth import get_user_model
from users.tests.test_helpers.model_factories import SuperUserFactory
from django.utils import timezone

User = get_user_model()


# Mock settings for GMB client ID and secret
@override_settings(
    GMB_CLIENT_ID="test_client_id",
    GMB_CLIENT_SECRET="test_client_secret",
    SITE_BASE_URL="http://testserver",
)
class GoogleMyBusinessCallbackViewTest(TestCase):
    def setUp(self):
        GoogleMyBusinessAccount.objects.all().delete()
        self.client = self.client_class()
        self.admin_user = SuperUserFactory(username="admin", email="admin@example.com", password="password")
        self.client.login(username="admin", password="password")

    @mock.patch("google_auth_oauthlib.flow.Flow.from_client_config")
    def test_successful_callback(self, mock_from_client_config):
        # Set a state in the session to simulate the auth flow initiation
        self.client.session["gmb_oauth_state"] = "test_state"
        self.client.session.save()

        mock_flow_instance = mock.Mock()
        mock_flow_instance.fetch_token.return_value = None
        mock_flow_instance.credentials = mock.Mock()
        mock_flow_instance.credentials.token = "mock_access_token"
        mock_flow_instance.credentials.refresh_token = "mock_refresh_token"
        mock_flow_instance.credentials.expiry = timezone.now() + timezone.timedelta(
            hours=1
        )
        mock_from_client_config.return_value = mock_flow_instance

        # Simulate Google's redirect with a code and the correct state
        response = self.client.get(
            reverse("dashboard:gmb_callback"),
            {"code": "test_code", "state": "test_state"},
        )

        # Assertions for successful flow
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("dashboard:gmb_settings"))

        messages = list(response.wsgi_request._messages)
        self.assertEqual(len(messages), 1)
        self.assertEqual(
            str(messages[0]), "Successfully connected to Google My Business!"
        )

        # Verify that tokens were saved to the database
        gmb_account = GoogleMyBusinessAccount.load()
        self.assertEqual(gmb_account.access_token, "mock_access_token")
        self.assertEqual(gmb_account.refresh_token, "mock_refresh_token")
        self.assertIsNotNone(gmb_account.token_expiry)

        # Verify fetch_token was called
        mock_flow_instance.fetch_token.assert_called_once()

    @mock.patch("google_auth_oauthlib.flow.Flow.from_client_config")
    def test_token_fetching_failure(self, mock_from_client_config):
        self.client.session["gmb_oauth_state"] = "test_state"
        self.client.session.save()

        mock_flow_instance = mock.Mock()
        mock_flow_instance.fetch_token.side_effect = Exception("Failed to get token")
        mock_from_client_config.return_value = mock_flow_instance

        response = self.client.get(
            reverse("dashboard:gmb_callback"),
            {"code": "test_code", "state": "test_state"},
        )

        # Assertions for failure scenario
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("dashboard:gmb_settings"))

        messages = list(response.wsgi_request._messages)
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Failed to fetch token: Failed to get token")

        # Verify that no tokens were saved (or they are still None)
        gmb_account = GoogleMyBusinessAccount.load()
        self.assertIsNone(gmb_account.access_token)
        self.assertIsNone(gmb_account.refresh_token)

    @mock.patch("google_auth_oauthlib.flow.Flow.from_client_config")
    def test_state_mismatch(self, mock_from_client_config):
        # Set a different state in the session
        self.client.session["gmb_oauth_state"] = "wrong_state"
        self.client.session.save()

        mock_flow_instance = mock.Mock()
        # Mock fetch_token to raise an exception if state mismatch occurs
        mock_flow_instance.fetch_token.side_effect = ValueError("State mismatch")
        mock_from_client_config.return_value = mock_flow_instance

        response = self.client.get(
            reverse("dashboard:gmb_callback"),
            {"code": "test_code", "state": "correct_state"},
        )

        # Assertions for state mismatch scenario
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("dashboard:gmb_settings"))

        messages = list(response.wsgi_request._messages)
        self.assertEqual(len(messages), 1)
        self.assertIn("Failed to fetch token", str(messages[0]))

    @mock.patch("google_auth_oauthlib.flow.Flow.from_client_config")
    def test_missing_state_in_session(self, mock_from_client_config):
        # Do not set 'gmb_oauth_state' in session
        mock_flow_instance = mock.Mock()
        mock_flow_instance.fetch_token.side_effect = ValueError("State missing")
        mock_from_client_config.return_value = mock_flow_instance

        response = self.client.get(
            reverse("dashboard:gmb_callback"),
            {"code": "test_code", "state": "some_state"},
        )

        # Assertions for missing state scenario
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("dashboard:gmb_settings"))

        messages = list(response.wsgi_request._messages)
        self.assertEqual(len(messages), 1)
        self.assertIn("Failed to fetch token", str(messages[0]))
