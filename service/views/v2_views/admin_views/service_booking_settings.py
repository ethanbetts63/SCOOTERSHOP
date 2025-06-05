from django.urls import reverse_lazy
from django.views.generic import UpdateView
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.forms import ValidationError

from service.models import ServiceSettings # Removed BlockedServiceDate
from service.forms import ServiceBookingSettingsForm # Removed BlockedServiceDateForm

class ServiceBookingSettingsView(UpdateView):
    """
    Class-based view for updating the singleton ServiceSettings model.
    This view handles displaying the current settings, processing form submissions,
    and managing messages for success or error.
    """
    model = ServiceSettings
    form_class = ServiceBookingSettingsForm
    template_name = 'service/service_booking_settings.html'
    success_url = reverse_lazy('service_settings') # Redirects to the same page on success

    def get_object(self, queryset=None):
        """
        Retrieves the single instance of ServiceSettings.
        If no instance exists, it creates one.
        """
        # Ensure only one instance of ServiceSettings exists.
        # This is a common pattern for singleton models.
        obj, created = ServiceSettings.objects.get_or_create(pk=1) # Assuming PK 1 for the singleton
        return obj

    def get_context_data(self, **kwargs):
        """
        No longer adds context for BlockedServiceDate forms or existing dates.
        """
        context = super().get_context_data(**kwargs)
        # Removed: context['blocked_service_date_form'] = BlockedServiceDateForm()
        # Removed: context['blocked_service_dates'] = BlockedServiceDate.objects.all().order_by('start_date')
        return context

    def form_valid(self, form):
        """
        Handles valid form submissions for ServiceSettings.
        Saves the form and adds a success message.
        """
        try:
            response = super().form_valid(form)
            messages.success(self.request, "Service settings updated successfully!")
            return response
        except ValidationError as e:
            # Add form-level errors from the model's clean method
            form.add_error(None, e)
            return self.form_invalid(form)


    def form_invalid(self, form):
        """
        Handles invalid form submissions for ServiceSettings.
        Adds an error message and renders the form again with errors.
        """
        messages.error(self.request, "There was an error updating service settings. Please correct the errors below.")
        return super().form_invalid(form)

    def post(self, request, *args, **kwargs):
        """
        Overrides the post method to only handle submissions from the main ServiceSettings form.
        Removed logic for BlockedServiceDate forms.
        """
        # Handle the ServiceSettings form submission
        if 'service_settings_submit' in request.POST:
            self.object = self.get_object()
            form = self.get_form()
            if form.is_valid():
                return self.form_valid(form)
            else:
                return self.form_invalid(form)

        # Removed: Handling for 'add_blocked_service_date_submit' and 'delete_blocked_service_date'
        # These actions are now assumed to be handled on a separate page.

        return super().post(request, *args, **kwargs) # Fallback for other POST requests

