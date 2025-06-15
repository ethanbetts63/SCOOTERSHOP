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
        
        condition_slug = self.kwargs.get('condition_slug')

        if condition_slug:
            if condition_slug == 'new':
                queryset = queryset.filter(conditions__name='new')
            elif condition_slug == 'used':
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
        
        condition_slug = self.kwargs.get('condition_slug')
        context['condition_type'] = condition_slug

        if condition_slug == 'new':
            context['page_title'] = "New Motorcycle Management"
        elif condition_slug == 'used':
            context['page_title'] = "Used/Demo/Hire Motorcycle Management"
        else:
            context['page_title'] = "All Motorcycle Inventory Management"
            
        return context

