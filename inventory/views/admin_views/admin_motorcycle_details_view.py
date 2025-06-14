# SCOOTER_SHOP/inventory/views/admin_views/admin_motorcycle_details_view.py

from django.shortcuts import get_object_or_404
from django.views.generic import DetailView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin

from inventory.models import Motorcycle

class AdminMotorcycleDetailsView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = Motorcycle
    template_name = 'inventory/admin_motorcycle_details.html'
    context_object_name = 'motorcycle'

    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = f"Motorcycle Details: {self.object.title}"
        return context

