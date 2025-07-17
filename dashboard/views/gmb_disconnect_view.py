from django.shortcuts import redirect
from django.views import View
from django.contrib import messages
from dashboard.models import GoogleMyBusinessAccount
from inventory.mixins import AdminRequiredMixin


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
        return redirect("dashboard:gmb_settings")
