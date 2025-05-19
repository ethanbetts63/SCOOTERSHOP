# dashboard/views/add_addon_view.py

from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin # Ensure only logged-in users can access
from ..forms.add_addon_form import AddAddOnForm # Import the form
from hire.models import AddOn # Import the AddOn model

class AddEditAddOnView(LoginRequiredMixin, View):
    template_name = 'dashboard/add_edit_addon.html' # We'll create this template
    form_class = AddAddOnForm

    def get(self, request, pk=None):
        if pk:
            # Editing an existing add-on
            addon = get_object_or_404(AddOn, pk=pk)
            form = self.form_class(instance=addon)
            title = f"Edit Add-On: {addon.name}"
        else:
            # Adding a new add-on
            form = self.form_class()
            title = "Add New Hire Add-On"

        context = {
            'form': form,
            'title': title,
            'is_edit': pk is not None,
        }
        return render(request, self.template_name, context)

    def post(self, request, pk=None):
        if pk:
            addon = get_object_or_404(AddOn, pk=pk)
            form = self.form_class(request.POST, instance=addon)
            success_message = "Add-On updated successfully!"
        else:
            form = self.form_class(request.POST)
            success_message = "Add-On added successfully!"

        if form.is_valid():
            form.save()
            messages.success(request, success_message)
            return redirect('dashboard:settings_hire_addons') # Redirect to the list view
        else:
            # If form is not valid, re-render the template with errors
            title = f"Edit Add-On: {addon.name}" if pk else "Add New Hire Add-On"
            messages.error(request, "Please correct the errors below.")
            context = {
                'form': form,
                'title': title,
                'is_edit': pk is not None,
            }
            return render(request, self.template_name, context)