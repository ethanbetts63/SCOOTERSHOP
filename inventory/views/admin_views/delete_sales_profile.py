# SCOOTER_SHOP/inventory/views/admin_views/sales_profile_delete_view.py

from django.shortcuts import redirect, get_object_or_404
from django.views import View
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin

from inventory.models import SalesProfile

class SalesProfileDeleteView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser

    def post(self, request, pk, *args, **kwargs):
        sales_profile = get_object_or_404(SalesProfile, pk=pk)
        try:
            profile_name = sales_profile.name # Store for message before deletion
            sales_profile.delete()
            messages.success(request, f'Sales profile for {profile_name} deleted successfully!')
        except Exception as e:
            messages.error(request, f'Error deleting sales profile for {sales_profile.name}: {e}')
        return redirect('inventory:sales_profile_management')

