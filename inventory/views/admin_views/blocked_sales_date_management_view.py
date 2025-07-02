from django.views.generic import ListView
from inventory.models import BlockedSalesDate
from inventory.mixins import AdminRequiredMixin


class BlockedSalesDateManagementView(AdminRequiredMixin, ListView):
    model = BlockedSalesDate
    template_name = "inventory/admin_blocked_sales_date_management.html"
    context_object_name = "blocked_sales_dates"
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset().order_by("start_date")
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Blocked Sales Dates Management"
        return context
