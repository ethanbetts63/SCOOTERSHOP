from django.test import TestCase, override_settings
from django.urls import reverse
from unittest import mock
from dashboard.models import GoogleMyBusinessAccount
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

# Mock settings for GMB client ID and secret
@override_settings(
    GMB_CLIENT_ID="test_client_id",
    GMB_CLIENT_SECRET="test_client_secret",
    # Mock SITE_BASE_URL for build_absolute_uri
    SITE_BASE_URL="http://testserver",
)
class GoogleMyBusinessAuthViewTest(TestCase):

    def setUp(self):
        # Ensure a clean state for each test
        GoogleMyBusinessAccount.objects.all().delete()
        self.client = self.client_class()
        
        # Create an admin user and log them in
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='password',
            is_staff=True,
            is_superuser=True
        )
        self.client.login(username='admin', password='password')

    @mock.patch('google_auth_oauthlib.flow.Flow.from_client_config')
    def test_auth_redirects_to_google(self, mock_from_client_config):
        mock_flow_instance = mock.Mock()
        mock_flow_instance.authorization_url.return_value = ("https://accounts.google.com/o/oauth2/auth?param=value", "test_state")
        mock_from_client_config.return_value = mock_flow_instance

        # Mock the credentials object that would be returned by fetch_token
        mock_flow_instance.credentials = mock.Mock()
        mock_flow_instance.credentials.token = "mock_access_token"
        mock_flow_instance.credentials.refresh_token = "mock_refresh_token"
        mock_flow_instance.credentials.expiry = timezone.now() + timezone.timedelta(hours=1)

        response = self.client.get(reverse('dashboard:gmb_auth'))

        # Test that it redirects to Google's authorization URL
        self.assertEqual(response.status_code, 302)
        self.assertIn("https://accounts.google.com/o/oauth2/auth", response.url)
        self.assertIn("param=value", response.url)

        # Test that the state is stored in the session
        self.assertIn('gmb_oauth_state', self.client.session)
        self.assertEqual(self.client.session['gmb_oauth_state'], "test_state")

        # Verify that Flow.from_client_config was called with correct arguments
        mock_from_client_config.assert_called_once()
        args, kwargs = mock_from_client_config.call_args
        client_config = args[0]
        self.assertEqual(client_config["web"]["client_id"], "test_client_id")
        self.assertEqual(client_config["web"]["client_secret"], "test_client_secret")
        self.assertIn('https://www.googleapis.com/auth/business.manage', kwargs['scopes'])

        # Verify redirect_uri was set on the flow instance
        expected_redirect_uri = self.client.get(reverse('dashboard:gmb_callback')).wsgi_request.build_absolute_uri(reverse('dashboard:gmb_callback'))
        self.assertEqual(mock_flow_instance.redirect_uri, expected_redirect_uri)

    def test_auth_redirects_if_already_configured(self):
        # Create a configured GMB account
        gmb_account = GoogleMyBusinessAccount.load()
        gmb_account.refresh_token = "some_refresh_token"
        gmb_account.save()

        response = self.client.get(reverse('dashboard:gmb_auth'))

        # Test that it redirects to gmb_settings
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('dashboard:gmb_settings'))

        # Test that an info message is added
        messages = list(response.wsgi_request._messages)
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "You are already connected to a Google My Business account.")
