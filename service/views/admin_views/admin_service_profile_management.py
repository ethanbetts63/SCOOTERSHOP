# service/views/admin_views.py (corrected)

from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
# from django.db.models import Q # Removed as search logic is now handled by AJAX in frontend

# Pagination imports
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

# Assuming AdminServiceProfileForm is in service.forms
from service.forms import AdminServiceProfileForm
from service.models import ServiceProfile

class ServiceProfileManagementView(LoginRequiredMixin, UserPassesTestMixin, View):
    """
    Admin view for managing (listing, creating, editing, and deleting) ServiceProfile instances.
    Now uses AJAX for search functionality on the frontend, so its own queryset filtering is simplified.
    Requires the user to be logged in and a staff member or superuser.
    """
    template_name = 'service/admin_service_profile_management.html'
    form_class = AdminServiceProfileForm
    paginate_by = 10 # Define items per page for server-side pagination of the initial list

    def test_func(self):
        """
        Ensures that only staff members or superusers can access this view.
        """
        return self.request.user.is_staff or self.request.user.is_superuser

    def get_profiles_for_display(self):
        """
        Builds the queryset for ServiceProfile instances for initial display and pagination.
        Filtering based on search term is now handled by the AJAX endpoint, so this
        method simply returns all profiles ordered by creation date.
        """
        return ServiceProfile.objects.all().order_by('-created_at')

    def get_context_data(self, **kwargs):
        """
        Adds context data, including the search term, form, and paginated profiles.
        """
        context = {}
        
        # Determine if we are in edit mode
        pk = kwargs.get('pk')
        instance = None
        is_edit_mode = False

        if pk:
            instance = get_object_or_404(ServiceProfile, pk=pk)
            form = self.form_class(instance=instance)
            is_edit_mode = True
        else:
            form = self.form_class()

        # Handle server-side pagination for the initial full list of profiles
        profile_list = self.get_profiles_for_display()
        paginator = Paginator(profile_list, self.paginate_by)
        page = self.request.GET.get('page')

        try:
            profiles_page = paginator.page(page)
        except PageNotAnInteger:
            # If page is not an integer, deliver first page.
            profiles_page = paginator.page(1)
        except EmptyPage:
            # If page is out of range (e.g. 9999), deliver last page of results.
            profiles_page = paginator.page(paginator.num_pages)

        context.update({
            'profiles': profiles_page, # Pass the paginated object for iterating
            'page_obj': profiles_page, # Also pass as page_obj for compatibility with pagination template
            'is_paginated': profiles_page.has_other_pages(), # Check if pagination is needed
            'form': form,
            'is_edit_mode': is_edit_mode,
            'current_profile': instance,
            'search_term': self.request.GET.get('q', '') # Keep for initial search box value in template
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
            # Redirect to the main management page after successful form submission
            return redirect(reverse('service:admin_service_profiles'))
        else:
            messages.error(request, "Please correct the errors below.")
            # If form is invalid, re-render the page with errors.
            # Re-use get_context_data to get profiles and search term, then update the form.
            context = self.get_context_data(pk=pk)
            context['form'] = form # Make sure the form with errors is passed back
            return render(request, self.template_name, context)

