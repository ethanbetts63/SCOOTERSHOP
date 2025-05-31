# payments/views/HireRefunds/admin_add_edit_refund_request_view.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views import View
from django.contrib import messages
from django.utils import timezone # Import timezone for setting processed_at

from payments.forms.admin_hire_refund_request_form import AdminHireRefundRequestForm
from payments.models.HireRefundRequest import HireRefundRequest

@method_decorator(login_required, name='dispatch')
class AdminAddEditRefundRequestView(View):
    """
    View for administrators to create or edit HireRefundRequest instances.
    This view handles both GET (displaying the form) and POST (processing form submission) requests.
    """
    template_name = 'payments/admin_hire_refund_form.html'

    def get(self, request, pk=None, *args, **kwargs):
        """
        Handles GET requests to display the refund request form.
        If a primary key (pk) is provided, it fetches an existing HireRefundRequest
        for editing; otherwise, it prepares a form for a new request.
        """
        hire_refund_request = None
        if pk:
            # Fetch the existing refund request instance for editing
            hire_refund_request = get_object_or_404(HireRefundRequest, pk=pk)
            form = AdminHireRefundRequestForm(instance=hire_refund_request)
            title = "Edit Hire Refund Request"
        else:
            # Create a new form instance for adding a new refund request
            form = AdminHireRefundRequestForm()
            title = "Create New Hire Refund Request"

        context = {
            'form': form,
            'title': title,
            'hire_refund_request': hire_refund_request, # Pass the instance for conditional rendering in template
        }
        return render(request, self.template_name, context)

    def post(self, request, pk=None, *args, **kwargs):
        """
        Handles POST requests to process the submitted refund request form.
        Validates the form data and saves/updates the HireRefundRequest instance.
        """
        hire_refund_request = None
        if pk:
            # Fetch the existing refund request instance for updating
            hire_refund_request = get_object_or_404(HireRefundRequest, pk=pk)
            form = AdminHireRefundRequestForm(request.POST, instance=hire_refund_request)
        else:
            # Create a new form instance with POST data
            form = AdminHireRefundRequestForm(request.POST)

        if form.is_valid():
            # Save the form data to create or update the HireRefundRequest instance
            refund_request_instance = form.save(commit=False)

            # Set is_admin_initiated to True, as this form is only for admin-initiated requests
            refund_request_instance.is_admin_initiated = True

            # If it's a new request or an existing one that was pending, set to 'reviewed_pending_approval'
            if not pk or refund_request_instance.status == 'pending':
                refund_request_instance.status = 'reviewed_pending_approval'

            # Automatically set processed_by and processed_at if status is approved or refunded
            if refund_request_instance.status in ['approved', 'refunded'] and not refund_request_instance.processed_by:
                refund_request_instance.processed_by = request.user
                refund_request_instance.processed_at = timezone.now()

            refund_request_instance.save() # Save the instance to the database

            messages.success(request, f"Hire Refund Request for booking '{refund_request_instance.hire_booking.booking_reference}' saved successfully! Current Status: {refund_request_instance.get_status_display()}")
            return redirect('dashboard:admin_hire_refund_management') # Redirect to the management page
        else:
            # If the form is not valid, re-render the form with errors
            messages.error(request, "Please correct the errors below.")
            title = "Edit Hire Refund Request" if pk else "Create New Hire Refund Request"
            context = {
                'form': form,
                'title': title,
                'hire_refund_request': hire_refund_request,
            }
            return render(request, self.template_name, context)

