# SCOOTER_SHOP/inventory/views/admin_views/sales_profile_details_view.py

from django.shortcuts import get_object_or_404
from django.views.generic import DetailView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin

from inventory.models import SalesProfile

class SalesProfileDetailsView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = SalesProfile
    template_name = 'inventory/admin_sales_profile_details.html'
    context_object_name = 'sales_profile'

    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = f"Sales Profile Details: {self.object.name}"
        return context

