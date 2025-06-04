# SCOOTER_SHOP/service/views/admin_views.py

from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView
from django.contrib import messages
from django.shortcuts import get_object_or_404

from service.models import ServiceType # Make sure this import is correct
from service.forms import ServiceTypeForm # Make sure this import is correct

class ServiceTypeCreateUpdateView(CreateView, UpdateView):
    """
    A combined view for creating and updating ServiceType instances.
    This view uses the same form (ServiceTypeForm) and template (add_edit_service_type.html)
    for both operations.
    """
    model = ServiceType
    form_class = ServiceTypeForm
    template_name = 'service/service_type_create_update.html'
    success_url = reverse_lazy('service:service_types_management') # Redirect to the service types list after success

    def get_object(self, queryset=None):
        """
        Overrides get_object to allow for creation (if no PK is provided in URL)
        or updating (if PK is provided).
        """
        pk = self.kwargs.get(self.pk_url_kwarg)
        if pk:
            # If a primary key is provided, retrieve the existing ServiceType
            return get_object_or_404(ServiceType, pk=pk)
        # If no primary key, it's a creation request, so return None (CreateView will handle it)
        return None

    def get_context_data(self, **kwargs):
        """
        Adds 'page_title' and 'service_type' (if editing) to the context.
        """
        context = super().get_context_data(**kwargs)
        if self.object: # If self.object exists, it means we are in update mode
            context['page_title'] = f'Edit Service Type: {self.object.name}'
            context['service_type'] = self.object # Pass the instance for template access (e.g., image URL)
        else:
            context['page_title'] = 'Add New Service Type'
        context['active_tab'] = 'service_types' # For dashboard navigation highlighting
        return context

    def form_valid(self, form):
        """
        Handles valid form submission. Adds a success message.
        """
        response = super().form_valid(form)
        if self.object.pk: # Check if the object has been saved (i.e., it's an update)
            messages.success(self.request, f"Service type '{self.object.name}' updated successfully!")
        else: # It's a new creation
            messages.success(self.request, f"Service type '{self.object.name}' added successfully!")
        return response

