from django.shortcuts import render, redirect, get_object_or_404
from django.utils.decorators import method_decorator
from django.views import View
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth.decorators import user_passes_test
from payments.forms.admin_refund_request_form import AdminRefundRequestForm
from payments.models.RefundRequest import RefundRequest
from payments.utils.create_refund_request import create_refund_request # Import the new utility
from users.views.auth import is_admin

@method_decorator(user_passes_test(is_admin), name='dispatch')
class AdminAddEditRefundRequestView(View):
    template_name = 'payments/admin_refund_form.html'

    def get(self, request, pk=None, *args, **kwargs):
        refund_request = None
        booking_reference = "N/A"

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
            elif refund_request.sales_booking:
                booking_reference = refund_request.sales_booking.sales_booking_reference
                title = f"Edit Sales Refund Request for Booking {booking_reference}"
        else:
            form = AdminRefundRequestForm()
            title = "Create New Refund Request"

        context = {
            'form': form,
            'title': title,
            'refund_request': refund_request,
            'booking_reference': booking_reference,
        }
        return render(request, self.template_name, context)

    def post(self, request, pk=None, *args, **kwargs):
        refund_request_instance = None
        if pk:
            refund_request_instance = get_object_or_404(RefundRequest, pk=pk)
            form = AdminRefundRequestForm(request.POST, instance=refund_request_instance)
        else:
            form = AdminRefundRequestForm(request.POST)

        admin_management_redirect_url = 'payments:admin_refund_management'

        if form.is_valid():
            # Extract data from the form
            amount_to_refund = form.cleaned_data.get('amount_to_refund')
            reason = form.cleaned_data.get('reason')
            rejection_reason = form.cleaned_data.get('rejection_reason') # Might be from reject form
            status = form.cleaned_data.get('status') # This is for direct setting in the form
            staff_notes = form.cleaned_data.get('staff_notes')
            hire_booking = form.cleaned_data.get('hire_booking') or (refund_request_instance.hire_booking if refund_request_instance else None)
            service_booking = form.cleaned_data.get('service_booking') or (refund_request_instance.service_booking if refund_request_instance else None)
            sales_booking = form.cleaned_data.get('sales_booking') or (refund_request_instance.sales_booking if refund_request_instance else None)
            payment = form.cleaned_data.get('payment') or (refund_request_instance.payment if refund_request_instance else None)
            driver_profile = form.cleaned_data.get('driver_profile') or (refund_request_instance.driver_profile if refund_request_instance else None)
            service_profile = form.cleaned_data.get('service_profile') or (refund_request_instance.service_profile if refund_request_instance else None)
            sales_profile = form.cleaned_data.get('sales_profile') or (refund_request_instance.sales_profile if refund_request_instance else None)


            if pk:
                refund_request_instance = form.save(commit=False)
                # Set processing details if status becomes approved/refunded and not set
                if refund_request_instance.status in ['approved', 'refunded', 'partially_refunded'] and not refund_request_instance.processed_by:
                    refund_request_instance.processed_by = request.user
                    refund_request_instance.processed_at = timezone.now()
                # Ensure is_admin_initiated is True if edited by admin
                refund_request_instance.is_admin_initiated = True
                refund_request_instance.save()

            else:
                # For new requests, use the utility function
                # Default status for admin-created requests is 'reviewed_pending_approval'
                refund_request_instance = create_refund_request(
                    amount_to_refund=amount_to_refund,
                    reason=reason, # or 'Admin Initiated Refund Request'
                    payment=payment,
                    hire_booking=hire_booking,
                    service_booking=service_booking,
                    sales_booking=sales_booking,
                    requesting_user=request.user, # The admin user
                    driver_profile=driver_profile,
                    service_profile=service_profile,
                    sales_profile=sales_profile,
                    is_admin_initiated=True,
                    staff_notes=staff_notes,
                    initial_status='reviewed_pending_approval', # Or 'approved' if you want it ready for Stripe immediately
                )
                if not refund_request_instance:
                    messages.error(request, "Failed to create new refund request.")
                    return render(request, self.template_name, {'form': form, 'title': "Create New Refund Request"})


            # Determine booking reference for success message and redirect
            booking_reference_for_msg = "N/A"
            if refund_request_instance.hire_booking:
                booking_reference_for_msg = refund_request_instance.hire_booking.booking_reference
            elif refund_request_instance.service_booking:
                booking_reference_for_msg = refund_request_instance.service_booking.service_booking_reference
            elif refund_request_instance.sales_booking:
                booking_reference_for_msg = refund_request_instance.sales_booking.sales_booking_reference


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
            elif refund_request_instance and refund_request_instance.sales_booking:
                 booking_reference_for_display = refund_request_instance.sales_booking.sales_booking_reference


            context = {
                'form': form,
                'title': title,
                'refund_request': refund_request_instance,
                'booking_reference': booking_reference_for_display,
            }
            return render(request, self.template_name, context)
