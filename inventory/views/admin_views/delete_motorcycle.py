# SCOOTER_SHOP/inventory/views/admin_views/motorcycle_delete_view.py

from django.shortcuts import redirect, get_object_or_404
from django.views import View
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin

from inventory.models import Motorcycle

class MotorcycleDeleteView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser

    def post(self, request, pk, *args, **kwargs):
        motorcycle = get_object_or_404(Motorcycle, pk=pk)
        try:
            motorcycle.delete()
            messages.success(request, f'Motorcycle "{motorcycle.title}" deleted successfully!')
        except Exception as e:
            messages.error(request, f'Error deleting motorcycle "{motorcycle.title}": {e}')
        return redirect('inventory:admin_inventory_management')

