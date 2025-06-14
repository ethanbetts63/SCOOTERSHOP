# inventory/views/admin_views/inventory_management_view.py

from django.db.models import Q
from django.views.generic import ListView
from inventory.models import Motorcycle
from inventory.mixins import AdminRequiredMixin

class InventoryManagementView(AdminRequiredMixin, ListView):
    model = Motorcycle
    template_name = 'inventory/admin_inventory_management.html'
    context_object_name = 'motorcycles'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset().order_by('-date_posted')
        search_term = self.request.GET.get('q', '').strip()

        if search_term:
            queryset = queryset.filter(
                Q(title__icontains=search_term) |
                Q(brand__icontains=search_term) |
                Q(model__icontains=search_term) |
                Q(vin_number__icontains=search_term) |
                Q(engine_number__icontains=search_term) |
                Q(stock_number__icontains=search_term) |
                Q(rego__icontains=search_term)
            ).distinct()

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_term'] = self.request.GET.get('q', '')
        context['page_title'] = "Motorcycle Inventory Management"
        return context
