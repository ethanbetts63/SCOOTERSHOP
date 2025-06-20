from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
# Assuming AdminServiceProfileForm is in service.forms
from service.forms import AdminServiceProfileForm
from service.models import ServiceProfile


class ServiceProfileCreateUpdateView(LoginRequiredMixin, UserPassesTestMixin, View):
    """
    Admin view for creating a new ServiceProfile or updating an existing one.
    Requires the user to be logged in and a staff member or superuser.
    """
    template_name = 'service/admin_service_profile_form.html' # New template name for form
    form_class = AdminServiceProfileForm

    def test_func(self):
        """
        Ensures that only staff members or superusers can access this view.
        """
        return self.request.user.is_staff or self.request.user.is_superuser

    def get(self, request, pk=None, *args, **kwargs):
        """
        Handles GET requests to display the form for creating a new profile
        or editing an existing one.
        """
        instance = None
        if pk:
            # If a primary key (pk) is provided, retrieve the specific profile to edit
            instance = get_object_or_404(ServiceProfile, pk=pk)
            form = self.form_class(instance=instance) # Pre-populate the form
        else:
            # If no pk, create a blank form for new profile
            form = self.form_class()

        context = {
            'form': form,
            'is_edit_mode': bool(pk), # True if pk exists, False otherwise
            'current_profile': instance # The profile being edited (None if creating new)
        }
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
            # Redirect back to the list view after successful creation/update
            return redirect(reverse('service:admin_service_profiles'))
        else:
            messages.error(request, "Please correct the errors below.")
            context = {
                'form': form, # Pass the form with errors back
                'is_edit_mode': bool(pk),
                'current_profile': instance
            }
            return render(request, self.template_name, context)
