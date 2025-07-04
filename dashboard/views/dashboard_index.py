from django.views.generic import TemplateView
from core.mixins import AdminRequiredMixin

class DashboardIndexView(AdminRequiredMixin, TemplateView):
    template_name = 'dashboard/dashboard_index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Admin Dashboard'
        return context
