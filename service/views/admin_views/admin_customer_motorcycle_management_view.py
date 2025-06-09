# service/views/admin_views.py (updated with CustomerMotorcycleListView)

from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Q # Import Q object for complex lookups
from django.views.generic import ListView # Import ListView for cleaner list management
from service.models import CustomerMotorcycle # Ensure CustomerMotorcycle and ServiceProfile are imported

class CustomerMotorcycleManagementView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """
    Admin view for listing CustomerMotorcycle instances with search functionality.
    Requires the user to be logged in and a staff member or superuser.
    """
    model = CustomerMotorcycle
    template_name = 'service/admin/customer_motorcycle_list.html' # New template
    context_object_name = 'motorcycles' # Variable name for the list in the template
    paginate_by = 10 # Optional: Add pagination for many motorcycles

    def test_func(self):
        """
        Ensures that only staff members or superusers can access this view.
        """
        return self.request.user.is_staff or self.request.user.is_superuser

    def get_queryset(self):
        """
        Builds the queryset for CustomerMotorcycle instances, applying search filters.
        Searchable fields: brand, model, rego, VIN, engine number.
        Also search by linked service_profile's name or email.
        """
        queryset = super().get_queryset().select_related('service_profile') # Optimize by pre-fetching service_profile
        search_term = self.request.GET.get('q', '').strip()

        if search_term:
            queryset = queryset.filter(
                Q(brand__icontains=search_term) |
                Q(model__icontains=search_term) |
                Q(rego__icontains=search_term) |
                Q(vin_number__icontains=search_term) |
                Q(engine_number__icontains=search_term) |
                Q(service_profile__name__icontains=search_term) | # Search by linked service profile name
                Q(service_profile__email__icontains=search_term) # Search by linked service profile email
            ).distinct() # Use distinct to avoid duplicates if a search term matches multiple fields
        return queryset.order_by('-created_at') # Order by most recently created first

    def get_context_data(self, **kwargs):
        """
        Adds context data, including the search term.
        """
        context = super().get_context_data(**kwargs)
        context['search_term'] = self.request.GET.get('q', '') # Pass the current search term to the template
        return context

