from django.urls import reverse_lazy
from django.views.generic import UpdateView
from django.contrib import messages

from core.mixins import AdminRequiredMixin
from dashboard.models import SiteSettings
from dashboard.forms import VisibilitySettingsForm

class SettingsVisibilityView(AdminRequiredMixin, UpdateView):
    model = SiteSettings
    form_class = VisibilitySettingsForm
    template_name = 'dashboard/settings_visibility.html'
    success_url = reverse_lazy('dashboard:settings_visibility')

    def get_object(self, queryset=None):
        return SiteSettings.get_settings()

    def form_valid(self, form):
        messages.success(self.request, 'Visibility settings updated successfully!')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Visibility Settings'
        context['active_tab'] = 'visibility'
        return context
