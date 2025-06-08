# payments/views/Refunds/admin_refund_policy_settings_view.py

from django.urls import reverse_lazy
from django.views.generic import UpdateView
from django.contrib import messages
from django.forms import ValidationError
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import user_passes_test

from payments.models import RefundPolicySettings
from payments.forms.refund_settings_form import RefundSettingsForm
from users.views.auth import is_admin # Assuming this utility exists for admin check


@method_decorator(user_passes_test(is_admin), name='dispatch')
class AdminRefundSettingsView(UpdateView):
    """
    Class-based view for updating the singleton RefundPolicySettings model.
    This view handles displaying the current settings, processing form submissions,
    and managing messages for success or error. It ensures only one instance exists.
    """
    model = RefundPolicySettings
    form_class = RefundSettingsForm
    template_name = 'payments/admin_refund_policy_settings.html'
    success_url = reverse_lazy('dashboard:admin_refund_policy_settings') # Redirects to the same page on success

    def get_object(self, queryset=None):
        """
        Retrieves the single instance of RefundPolicySettings (pk=1).
        If no instance exists, it creates one.
        """
        obj, created = RefundPolicySettings.objects.get_or_create(pk=1)
        return obj

    def form_valid(self, form):
        """
        Handles valid form submissions for RefundPolicySettings.
        Saves the form and adds a success message.
        """
        try:
            response = super().form_valid(form)
            messages.success(self.request, "Refund Policy settings updated successfully!")
            return response
        except ValidationError as e:
            # Add form-level errors from the model's clean method (if not already added by form.clean)
            form.add_error(None, e)
            return self.form_invalid(form)

    def form_invalid(self, form):
        """
        Handles invalid form submissions for RefundPolicySettings.
        Adds an error message and renders the form again with errors.
        """
        messages.error(self.request, "There was an error updating refund policy settings. Please correct the errors below.")
        return super().form_invalid(form)

    def post(self, request, *args, **kwargs):
        """
        Overrides the post method to only handle submissions from the main RefundPolicySettings form.
        """
        if 'refund_policy_settings_submit' in request.POST:
            self.object = self.get_object() # Ensure self.object is set for form_valid/invalid
            form = self.get_form()
            if form.is_valid():
                return self.form_valid(form)
            else:
                return self.form_invalid(form)
        return super().post(request, *args, **kwargs) # Fallback for other POST requests, though unlikely here
