# inventory/views/admin_views/inventory_settings_view.py

from django.urls import reverse_lazy
from django.views.generic import UpdateView
from django.contrib import messages
from django.forms import ValidationError

from inventory.models import InventorySettings # Import the InventorySettings model
from inventory.forms.admin_inventory_settings_form import InventorySettingsForm # Import the new form

class InventorySettingsView(UpdateView):
    """
    Class-based view for updating the singleton InventorySettings model.
    This view handles displaying the current settings, processing form submissions,
    and managing messages for success or error.
    """
    model = InventorySettings
    form_class = InventorySettingsForm # Use the new InventorySettingsForm
    template_name = 'inventory/admin_inventory_settings.html' # Link to the new template
    success_url = reverse_lazy('inventory:inventory_settings') # Redirects to the same page on success

    def get_object(self, queryset=None):
        """
        Retrieves the single instance of InventorySettings.
        If no instance exists, it creates one.
        """
        # Ensure only one instance of InventorySettings exists.
        # This is a common pattern for singleton models.
        obj, created = InventorySettings.objects.get_or_create(pk=1) # Assuming PK 1 for the singleton
        return obj

    def form_valid(self, form):
        """
        Handles valid form submissions for InventorySettings.
        Saves the form and adds a success message.
        """
        try:
            response = super().form_valid(form)
            messages.success(self.request, "Inventory settings updated successfully!")
            return response
        except ValidationError as e:
            # Add form-level errors from the model's clean method
            form.add_error(None, e)
            return self.form_invalid(form)

    def form_invalid(self, form):
        """
        Handles invalid form submissions for InventorySettings.
        Adds an error message and renders the form again with errors.
        """
        messages.error(self.request, "There was an error updating inventory settings. Please correct the errors below.")
        return super().form_invalid(form)

    def post(self, request, *args, **kwargs):
        """
        Overrides the post method to only handle submissions from the main InventorySettings form.
        """
        # Handle the InventorySettings form submission
        if 'inventory_settings_submit' in request.POST: # Changed name attribute for clarity
            self.object = self.get_object()
            form = self.get_form()
            if form.is_valid():
                return self.form_valid(form)
            else:
                return self.form_invalid(form)

        return super().post(request, *args, **kwargs) # Fallback for other POST requests
