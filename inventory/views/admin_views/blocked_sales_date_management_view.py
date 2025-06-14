# SCOOTER_SHOP/inventory/views/admin_views/blocked_sales_date_management_view.py

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView
from inventory.models import BlockedSalesDate

class BlockedSalesDateManagementView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = BlockedSalesDate
    template_name = 'inventory/admin_blocked_sales_date_management.html'
    context_object_name = 'blocked_sales_dates'
    paginate_by = 10

    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser

    def get_queryset(self):
        # Removed search term logic as requested
        queryset = super().get_queryset().order_by('start_date')
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Removed search_term from context as requested
        context['page_title'] = "Blocked Sales Dates Management"
        return context

