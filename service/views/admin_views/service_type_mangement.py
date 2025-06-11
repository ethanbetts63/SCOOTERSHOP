# service/views/admin_service_type_management.py

from django.shortcuts import render
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin

from service.models import ServiceType # Import the ServiceType model

class ServiceTypeManagementView(LoginRequiredMixin, UserPassesTestMixin, View):
    """
    Admin view for managing (listing) ServiceType instances without pagination.
    Requires the user to be logged in and a staff member or superuser.
    """
    template_name = 'service/admin_service_type_management.html'

    def test_func(self):
        """
        Ensures that only staff members or superusers can access this view.
        """
        return self.request.user.is_staff or self.request.user.is_superuser

    def get_service_types_for_display(self):
        """
        Builds the queryset for ServiceType instances for display.
        This method now simply returns all profiles ordered by name, as pagination is removed.
        """
        return ServiceType.objects.all().order_by('name') # Order by name for consistency

    def get(self, request, *args, **kwargs):
        """
        Handles GET requests to display the list of service types.
        """
        service_types = self.get_service_types_for_display()

        context = {
            'service_types': service_types, # Pass all service types directly
            # No 'page_obj' or 'is_paginated' needed as pagination is removed
        }
        return render(request, self.template_name, context)

