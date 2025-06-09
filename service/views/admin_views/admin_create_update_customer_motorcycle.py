
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from service.forms import AdminCustomerMotorcycleForm 
from service.models import CustomerMotorcycle # Ensure CustomerMotorcycle and ServiceProfile are imported



class CustomerMotorcycleCreateUpdateView(LoginRequiredMixin, UserPassesTestMixin, View):
    """
    Admin view for creating a new CustomerMotorcycle or updating an existing one.
    Handles GET for displaying the form and POST for processing submissions.
    Requires the user to be logged in and a staff member or superuser.
    """
    template_name = 'service/admin_customer_motorcycle_create_update.html' # New template
    form_class = AdminCustomerMotorcycleForm

    def test_func(self):
        """
        Ensures that only staff members or superusers can access this view.
        """
        return self.request.user.is_staff or self.request.user.is_superuser

    def get(self, request, pk=None, *args, **kwargs):
        """
        Handles GET requests to display the form.
        If pk is provided, pre-populates the form with existing motorcycle data.
        """
        instance = None
        if pk:
            # If a primary key (pk) is provided, retrieve the specific motorcycle to edit
            instance = get_object_or_404(CustomerMotorcycle, pk=pk)
            form = self.form_class(instance=instance) # Pre-populate the form
        else:
            # If no pk, create a blank form for a new motorcycle
            form = self.form_class()

        context = {
            'form': form,
            'is_edit_mode': bool(pk), # True if pk exists, False otherwise
            'current_motorcycle': instance # The motorcycle being edited (None if creating new)
        }
        return render(request, self.template_name, context)

    def post(self, request, pk=None, *args, **kwargs):
        """
        Handles POST requests for form submission (creating or updating a CustomerMotorcycle).
        Supports file uploads for the 'image' field.
        """
        instance = None
        if pk:
            instance = get_object_or_404(CustomerMotorcycle, pk=pk)
            # Pass instance and request.FILES for file uploads
            form = self.form_class(request.POST, request.FILES, instance=instance)
        else:
            # Pass request.FILES for new file uploads
            form = self.form_class(request.POST, request.FILES)

        if form.is_valid():
            customer_motorcycle = form.save()
            if pk:
                messages.success(request, f"Motorcycle '{customer_motorcycle}' updated successfully.")
            else:
                messages.success(request, f"Motorcycle '{customer_motorcycle}' created successfully.")
            # Redirect back to the motorcycle list view after successful creation/update
            return redirect(reverse('service:admin_customer_motorcycle_management'))
        else:
            messages.error(request, "Please correct the errors below.")
            context = {
                'form': form, # Pass the form with errors back
                'is_edit_mode': bool(pk),
                'current_motorcycle': instance
            }
            return render(request, self.template_name, context)
