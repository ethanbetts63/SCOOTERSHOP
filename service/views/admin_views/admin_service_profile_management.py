# service/views/admin_views.py (corrected)

from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Q # Import Q object for complex lookups

# Assuming AdminServiceProfileForm is in service.forms
from service.forms import AdminServiceProfileForm
from service.models import ServiceProfile

class ServiceProfileManagementView(LoginRequiredMixin, UserPassesTestMixin, View):
    """
    Admin view for managing (listing, creating, editing, and deleting) ServiceProfile instances.
    Includes search functionality.
    Requires the user to be logged in and a staff member or superuser.
    """
    template_name = 'service/admin_service_profile_management.html'
    form_class = AdminServiceProfileForm

    def test_func(self):
        """
        Ensures that only staff members or superusers can access this view.
        """
        return self.request.user.is_staff or self.request.user.is_superuser

    def get_queryset(self):
        """
        Builds the queryset for ServiceProfile instances, applying search filters.
        """
        queryset = ServiceProfile.objects.all().order_by('-created_at')
        search_term = self.request.GET.get('q', '').strip()

        if search_term:
            # Filter by name, email, phone_number, city, or linked user's username/email
            queryset = queryset.filter(
                Q(name__icontains=search_term) |
                Q(email__icontains=search_term) |
                Q(phone_number__icontains=search_term) |
                Q(address_line_1__icontains=search_term) | # Added address line 1
                Q(address_line_2__icontains=search_term) | # Added address line 2
                Q(city__icontains=search_term) |
                Q(state__icontains=search_term) | # Added state
                Q(post_code__icontains=search_term) | # Added post code
                Q(country__icontains=search_term) | # Added country
                Q(user__username__icontains=search_term) | # Search by linked user's username
                Q(user__email__icontains=search_term)      # Search by linked user's email
            ).distinct() # Use distinct to avoid duplicate profiles if a search term matches multiple fields
        return queryset

    def get_context_data(self, **kwargs):
        """
        Adds context data, including the search term and the form.
        """
        # Initialize context directly, as View does not have get_context_data
        context = {}
        
        # Populate the form based on whether we are editing an instance
        pk = kwargs.get('pk')
        instance = None
        is_edit_mode = False

        if pk:
            instance = get_object_or_404(ServiceProfile, pk=pk)
            form = self.form_class(instance=instance)
            is_edit_mode = True
        else:
            form = self.form_class()

        context.update({
            'profiles': self.get_queryset(), # Use the filtered queryset for display
            'form': form,
            'is_edit_mode': is_edit_mode,
            'current_profile': instance,
            'search_term': self.request.GET.get('q', '') # Pass the current search term to the template
        })
        return context

    def get(self, request, pk=None, *args, **kwargs):
        """
        Handles GET requests to display the list of service profiles and the form
        for creating a new one or editing an existing one, with search capabilities.
        """
        context = self.get_context_data(pk=pk)
        return render(request, self.template_name, context)

    def post(self, request, pk=None, *args, **kwargs):
        """
        Handles POST requests for form submission (creating or updating a ServiceProfile).
        """
        instance = None
        if pk:
            instance = get_object_or_404(ServiceProfile, pk=pk)
            form = self.form_class(request.POST, instance=instance)
        else:
            form = self.form_class(request.POST)

        if form.is_valid():
            service_profile = form.save()
            if pk:
                messages.success(request, f"Service Profile for '{service_profile.name}' updated successfully.")
            else:
                messages.success(request, f"Service Profile for '{service_profile.name}' created successfully.")
            return redirect(reverse('service:admin_service_profiles'))
        else:
            messages.error(request, "Please correct the errors below.")
            # If form is invalid, we need to re-render the page with the errors,
            # so we prepare the context using get_context_data and then update the form.
            context = self.get_context_data(pk=pk) # Re-use get_context_data to get profiles and search term
            context['form'] = form # Make sure the form with errors is passed back
            return render(request, self.template_name, context)

class ServiceProfileDeleteView(LoginRequiredMixin, UserPassesTestMixin, View):
    """
    Admin view for deleting a ServiceProfile instance.
    Requires staff status to access.
    """
    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser

    def post(self, request, pk, *args, **kwargs):
        profile = get_object_or_404(ServiceProfile, pk=pk)
        profile_name = profile.name # Store name before deletion for message
        profile.delete()
        messages.success(request, f"Service Profile for '{profile_name}' deleted successfully.")
        return redirect(reverse('service:admin_service_profiles'))

