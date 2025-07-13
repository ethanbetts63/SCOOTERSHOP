# Create a new file: dashboard/views/gmb_auth_views.py
import google_auth_oauthlib.flow
import googleapiclient.discovery
from django.shortcuts import redirect, reverse
from django.views import View
from django.conf import settings
from django.contrib import messages
from dashboard.models import GoogleMyBusinessAccount
from inventory.mixins import AdminRequiredMixin

# This is the scope required to access GMB account and review data.
GMB_SCOPES = ['https://www.googleapis.com/auth/business.manage']

class GoogleMyBusinessAuthView(AdminRequiredMixin, View):
    """
    Initiates the OAuth 2.0 flow by redirecting the user to Google's consent screen.
    """
    def get(self, request, *args, **kwargs):
        gmb_account = GoogleMyBusinessAccount.load()
        if gmb_account.is_configured:
            messages.info(request, "You are already connected to a Google My Business account.")
            return redirect('dashboard:gmb_settings')

        # Use the google-auth-oauthlib library to create the flow.
        # The client_secrets.json is constructed on the fly from Django settings.
        client_config = {
            "web": {
                "client_id": settings.GMB_CLIENT_ID,
                "client_secret": settings.GMB_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [request.build_absolute_uri(reverse('dashboard:gmb_callback'))]
            }
        }

        flow = google_auth_oauthlib.flow.Flow.from_client_config(
            client_config,
            scopes=GMB_SCOPES
        )

        # The URI that Google will redirect the user to after the user has granted or denied consent.
        flow.redirect_uri = request.build_absolute_uri(reverse('dashboard:gmb_callback'))
        
        # Generate the authorization URL and store the state in the session.
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent' # Force prompt for refresh token
        )
        request.session['gmb_oauth_state'] = state

        return redirect(authorization_url)


class GoogleMyBusinessCallbackView(AdminRequiredMixin, View):
    """
    Handles the callback from Google after the user has authenticated.
    """
    def get(self, request, *args, **kwargs):
        state = request.session.get('gmb_oauth_state')
        
        # Construct the flow again, same as in the initiation view.
        client_config = {
            "web": {
                "client_id": settings.GMB_CLIENT_ID,
                "client_secret": settings.GMB_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [request.build_absolute_uri(reverse('dashboard:gmb_callback'))]
            }
        }

        flow = google_auth_oauthlib.flow.Flow.from_client_config(
            client_config,
            scopes=GMB_SCOPES,
            state=state
        )
        flow.redirect_uri = request.build_absolute_uri(reverse('dashboard:gmb_callback'))

        # Use the authorization server's response to fetch the OAuth 2.0 tokens.
        try:
            flow.fetch_token(authorization_response=request.build_absolute_uri())
        except Exception as e:
            messages.error(request, f"Failed to fetch token: {e}")
            return redirect('dashboard:gmb_settings')

        credentials = flow.credentials
        
        # Save the credentials to the database.
        gmb_account = GoogleMyBusinessAccount.load()
        gmb_account.access_token = credentials.token
        gmb_account.refresh_token = credentials.refresh_token
        gmb_account.token_expiry = credentials.expiry
        gmb_account.save()

        messages.success(request, "Successfully connected to Google My Business!")
        return redirect('dashboard:gmb_settings')

class GoogleMyBusinessDisconnectView(AdminRequiredMixin, View):
    """
    Disconnects the GMB account by clearing the stored credentials.
    """
    def post(self, request, *args, **kwargs):
        gmb_account = GoogleMyBusinessAccount.load()
        gmb_account.account_id = None
        gmb_account.location_id = None
        gmb_account.access_token = None
        gmb_account.refresh_token = None
        gmb_account.token_expiry = None
        gmb_account.save()
        messages.success(request, "Successfully disconnected from Google My Business.")
        return redirect('dashboard:gmb_settings')
