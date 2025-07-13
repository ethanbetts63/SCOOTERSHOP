import google_auth_oauthlib.flow
from django.shortcuts import redirect, reverse
from django.views import View
from django.conf import settings
from django.contrib import messages
from dashboard.models import GoogleMyBusinessAccount
from inventory.mixins import AdminRequiredMixin


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
