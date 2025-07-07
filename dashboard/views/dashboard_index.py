from django.views.generic import TemplateView
from django.shortcuts import redirect
from django.views import View
from core.mixins import AdminRequiredMixin
from ..models import Notification

class DashboardIndexView(AdminRequiredMixin, TemplateView):
    template_name = 'dashboard/dashboard_index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Admin Dashboard'
        context['notifications'] = Notification.objects.filter(is_cleared=False)
        return context

class ClearNotificationsView(AdminRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        Notification.objects.filter(is_cleared=False).update(is_cleared=True)
        return redirect('dashboard:dashboard_index')
