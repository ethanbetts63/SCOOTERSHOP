# inventory/views/admin_views/inventory_management_view.py

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Q
from django.views.generic import ListView
from inventory.models import Motorcycle

class InventoryManagementView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """
    Admin view for listing and managing all motorcycle inventory with search.
    Requires the user to be a staff member or superuser.
    """
    model = Motorcycle
    template_name = 'inventory/admin_inventory_management.html'
    context_object_name = 'motorcycles'
    paginate_by = 10

    def test_func(self):
        """
        Ensure that only staff or superusers can access this page.
        """
        return self.request.user.is_staff or self.request.user.is_superuser

    def get_queryset(self):
        """
        Builds the queryset for Motorcycle instances, applying search filters.
        Searchable fields include title, brand, model, VIN, engine number,
        stock number, and registration.
        """
        # Start with all motorcycles, ordered by the most recently posted
        queryset = super().get_queryset().order_by('-date_posted')
        search_term = self.request.GET.get('q', '').strip()

        if search_term:
            # Apply filters if a search term is provided
            queryset = queryset.filter(
                Q(title__icontains=search_term) |
                Q(brand__icontains=search_term) |
                Q(model__icontains=search_term) |
                Q(vin_number__icontains=search_term) |
                Q(engine_number__icontains=search_term) |
                Q(stock_number__icontains=search_term) |
                Q(rego__icontains=search_term)
            ).distinct()  # Use distinct to prevent duplicates in results

        return queryset

    def get_context_data(self, **kwargs):
        """
        Adds additional context data for the template.
        """
        context = super().get_context_data(**kwargs)
        # Pass the current search term back to the template
        context['search_term'] = self.request.GET.get('q', '')
        # Set a title for the page
        context['page_title'] = "Motorcycle Inventory Management"
        return context
