# inventory/views/admin_views/inventory_management_view.py

from django.db.models import Q
from django.views.generic import ListView
from inventory.models import Motorcycle # No need to import MotorcycleCondition directly here for filtering
from inventory.mixins import AdminRequiredMixin


class InventoryManagementView(AdminRequiredMixin, ListView):
    model = Motorcycle
    template_name = 'inventory/admin_inventory_management.html'
    context_object_name = 'motorcycles'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset().order_by('-date_posted')
        
        # Get the condition slug from URL kwargs (e.g., 'new', 'used')
        # Defaults to None if not provided (for the 'all' view)
        condition_slug = self.kwargs.get('condition_slug')

        if condition_slug:
            if condition_slug == 'new':
                # Filter for motorcycles explicitly tagged with the 'new' condition
                queryset = queryset.filter(conditions__name='new')
            elif condition_slug == 'used':
                # Filter for motorcycles with 'used', 'demo', or 'hire' conditions
                queryset = queryset.filter(conditions__name__in=['used', 'demo', 'hire'])

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
        
        # Pass the condition slug to the template
        condition_slug = self.kwargs.get('condition_slug')
        context['condition_type'] = condition_slug # Use this in template for conditional display

        if condition_slug == 'new':
            context['page_title'] = "New Motorcycle Management"
        elif condition_slug == 'used':
            context['page_title'] = "Used/Demo/Hire Motorcycle Management"
        else:
            context['page_title'] = "All Motorcycle Inventory Management"
            
        return context

