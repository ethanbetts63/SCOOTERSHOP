from django.shortcuts import redirect, get_object_or_404
from django.views import View
from django.contrib import messages
from inventory.mixins import AdminRequiredMixin

from inventory.models import Motorcycle


class MotorcycleDeleteView(AdminRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        motorcycle = get_object_or_404(Motorcycle, pk=pk)
        try:
            motorcycle.delete()
            messages.success(
                request, f'Motorcycle "{motorcycle.title}" deleted successfully!'
            )
        except Exception as e:
            messages.error(
                request, f'Error deleting motorcycle "{motorcycle.title}": {e}'
            )
        return redirect("inventory:admin_inventory_management")
