from django.shortcuts import redirect, get_object_or_404
from django.views import View
from django.contrib import messages
from inventory.mixins import AdminRequiredMixin

from inventory.models.color import Color


class ColorDeleteView(AdminRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        color_to_delete = get_object_or_404(Color, pk=pk)
        color_name = color_to_delete.name
        try:
            color_to_delete.delete()
            messages.success(
                request, f"Color '{color_name}' deleted successfully."
            )
        except Exception as e:
            messages.error(request, f"Error deleting color: {e}")

        return redirect("inventory:color_management")
