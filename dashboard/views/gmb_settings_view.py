# Create a new file: dashboard/views/gmb_settings_view.py
from django.shortcuts import render
from django.views import View
from inventory.mixins import AdminRequiredMixin
from dashboard.models import GoogleMyBusinessAccount


class GoogleMyBusinessSettingsView(AdminRequiredMixin, View):
    """
    Renders the settings page for managing the GMB connection.
    """

    template_name = "dashboard/admin_gmb_settings.html"

    def get(self, request, *args, **kwargs):
        gmb_account = GoogleMyBusinessAccount.load()
        context = {"page_title": "GMB Integration Settings", "gmb_account": gmb_account}
        return render(request, self.template_name, context)
