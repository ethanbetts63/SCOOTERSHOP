from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views import View
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth.decorators import user_passes_test
# Import the (soon-to-be) generalized AdminRefundRequestForm
from payments.forms.admin_refund_request_form import AdminRefundRequestForm 
from payments.models.RefundRequest import RefundRequest
from users.views.auth import is_admin # Assuming this utility exists for admin check

# Import booking models to access their specific fields
from hire.models import HireBooking
from service.models import ServiceBooking


@method_decorator(user_passes_test(is_admin), name='dispatch')
class AdminAddEditRefundRequestView(View):
    """
    View for administrators to create or edit RefundRequest instances for
    both HireBookings and ServiceBookings.
    This view handles both GET (displaying the form) and POST (processing form submission) requests.
    """
    template_name = 'payments/admin_refund_request_form.html' # Changed to a generic template name

    def get(self, request, pk=None, *args, **kwargs):
        """
        Handles GET requests to display the refund request form.
        If a primary key (pk) is provided, it fetches an existing RefundRequest
        for editing; otherwise, it prepares a form for a new request.
        """
        refund_request = None # Use generic name
        booking_reference = "N/A" # For display in title

        if pk:
            refund_request = get_object_or_404(RefundRequest, pk=pk)
            form = AdminRefundRequestForm(instance=refund_request)
            title = "Edit Refund Request"

            if refund_request.hire_booking:
                booking_reference = refund_request.hire_booking.booking_reference
                title = f"Edit Hire Refund Request for Booking {booking_reference}"
            elif refund_request.service_booking:
                booking_reference = refund_request.service_booking.service_booking_reference
                title = f"Edit Service Refund Request for Booking {booking_reference}"
        else:
            form = AdminRefundRequestForm()
            title = "Create New Refund Request"

        context = {
            'form': form,
            'title': title,
            'refund_request': refund_request, # Use generic name
            'booking_reference': booking_reference, # Pass for template display
        }
        return render(request, self.template_name, context)

    def post(self, request, pk=None, *args, **kwargs):
        """
        Handles POST requests to process the submitted refund request form.
        Validates the form data and saves/updates the RefundRequest instance.
        """
        refund_request_instance = None # Use generic name
        if pk:
            refund_request_instance = get_object_or_404(RefundRequest, pk=pk)
            form = AdminRefundRequestForm(request.POST, instance=refund_request_instance)
        else:
            form = AdminRefundRequestForm(request.POST)

        # Determine the redirect URL for admin management based on booking type
        # This assumes separate admin views for hire and service refund management
        admin_management_redirect_url = 'dashboard:admin_refund_management_list' # Generic fallback

        if form.is_valid():
            refund_request_instance = form.save(commit=False)

            refund_request_instance.is_admin_initiated = True

            # Logic for initial status setting when creating a new request or
            # transitioning a pending request to 'reviewed_pending_approval'
            if not pk: # This is a new request created by admin
                # If admin is creating, assume it's ready for review unless explicitly set otherwise
                refund_request_instance.status = 'reviewed_pending_approval'
            elif refund_request_instance.status == 'pending': # Existing request was user-submitted and unverified
                refund_request_instance.status = 'reviewed_pending_approval'


            # If status is approved or refunded, and processed_by is not set, set it.
            # This ensures only the first approval/refund record the processor.
            if refund_request_instance.status in ['approved', 'refunded', 'partially_refunded'] and not refund_request_instance.processed_by:
                refund_request_instance.processed_by = request.user
                refund_request_instance.processed_at = timezone.now()

            refund_request_instance.save()

            # Determine booking reference for success message and redirect
            booking_reference_for_msg = "N/A"
            if refund_request_instance.hire_booking:
                booking_reference_for_msg = refund_request_instance.hire_booking.booking_reference
                admin_management_redirect_url = 'dashboard:admin_hire_refund_management'
            elif refund_request_instance.service_booking:
                booking_reference_for_msg = refund_request_instance.service_booking.service_booking_reference
                admin_management_redirect_url = 'dashboard:admin_service_refund_management'


            messages.success(request, f"Refund Request for booking '{booking_reference_for_msg}' saved successfully! Current Status: {refund_request_instance.get_status_display()}")
            return redirect(admin_management_redirect_url)
        else:
            messages.error(request, "Please correct the errors below.")
            title = "Edit Refund Request" if pk else "Create New Refund Request"
            booking_reference_for_display = "N/A"
            if refund_request_instance and refund_request_instance.hire_booking:
                 booking_reference_for_display = refund_request_instance.hire_booking.booking_reference
            elif refund_request_instance and refund_request_instance.service_booking:
                 booking_reference_for_display = refund_request_instance.service_booking.service_booking_reference


            context = {
                'form': form,
                'title': title,
                'refund_request': refund_request_instance, # Use generic name
                'booking_reference': booking_reference_for_display, # Pass for template display
            }
            return render(request, self.template_name, context)

