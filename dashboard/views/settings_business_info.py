from django.urls import reverse_lazy
from django.views.generic import UpdateView
from django.contrib import messages

from core.mixins import AdminRequiredMixin
from dashboard.models import SiteSettings
from dashboard.forms import BusinessInfoForm


class SettingsBusinessInfoView(AdminRequiredMixin, UpdateView):
    model = SiteSettings
    form_class = BusinessInfoForm
    template_name = "dashboard/settings_business_info.html"
    success_url = reverse_lazy("dashboard:settings_business_info")

    def get_object(self, queryset=None):
        return SiteSettings.get_settings()

    def form_valid(self, form):
        messages.success(self.request, "Business information updated successfully!")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Business Information Settings"
        context["active_tab"] = "business_info"
        return context
