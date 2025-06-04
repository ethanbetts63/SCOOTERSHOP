from django.urls import reverse_lazy
from django.views.generic import UpdateView
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.forms import ValidationError

from service.models import ServiceSettings, BlockedServiceDate
from service.forms import ServiceBookingSettingsForm, BlockedServiceDateForm

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
        Adds the form for BlockedServiceDate and existing blocked dates to the context.
        """
        context = super().get_context_data(**kwargs)
        # Initialize the BlockedServiceDateForm for adding new blocked dates
        context['blocked_service_date_form'] = BlockedServiceDateForm()
        # Retrieve all existing blocked service dates to display
        context['blocked_service_dates'] = BlockedServiceDate.objects.all().order_by('start_date')
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
        Overrides the post method to handle submissions from both forms on the page:
        ServiceSettingsUpdateView's form and the BlockedServiceDateForm.
        """
        # Handle the ServiceSettings form submission
        if 'service_settings_submit' in request.POST:
            self.object = self.get_object()
            form = self.get_form()
            if form.is_valid():
                return self.form_valid(form)
            else:
                return self.form_invalid(form)

        # Handle BlockedServiceDate form submission
        elif 'add_blocked_service_date_submit' in request.POST:
            blocked_form = BlockedServiceDateForm(request.POST)
            if blocked_form.is_valid():
                blocked_form.save()
                messages.success(request, "Blocked date added successfully!")
                return redirect(self.get_success_url())
            else:
                # If blocked date form is invalid, re-render the page with errors
                # We need to re-initialize the main form and all context data
                self.object = self.get_object() # Get the ServiceSettings instance
                form = self.get_form() # Get the ServiceSettings form
                context = self.get_context_data(form=form) # Get context with main form
                context['blocked_service_date_form'] = blocked_form # Add the invalid blocked form
                messages.error(request, "There was an error adding the blocked date. Please correct the errors below.")
                return self.render_to_response(context)

        # Handle deletion of a blocked service date
        elif 'delete_blocked_service_date' in request.POST:
            blocked_date_id = request.POST.get('delete_blocked_service_date')
            blocked_date = get_object_or_404(BlockedServiceDate, pk=blocked_date_id)
            blocked_date.delete()
            messages.success(request, "Blocked date deleted successfully!")
            return redirect(self.get_success_url())

        return super().post(request, *args, **kwargs) # Fallback for other POST requests
