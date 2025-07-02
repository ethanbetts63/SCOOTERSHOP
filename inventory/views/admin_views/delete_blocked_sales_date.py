from django.shortcuts import redirect, get_object_or_404
from django.views import View
from django.contrib import messages
from inventory.mixins import AdminRequiredMixin

from inventory.models import BlockedSalesDate


class BlockedSalesDateDeleteView(AdminRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        blocked_date = get_object_or_404(BlockedSalesDate, pk=pk)
        try:
            blocked_date.delete()
            messages.success(
                request, f"Blocked sales date {blocked_date} deleted successfully!"
            )
        except Exception as e:
            messages.error(
                request, f"Error deleting blocked sales date {blocked_date}: {e}"
            )
        return redirect("inventory:blocked_sales_date_management")
