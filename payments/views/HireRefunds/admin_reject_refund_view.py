# payments/views/HireRefunds/admin_reject_refund_view.py

from django.shortcuts import render, redirect, get_object_or_404
from django.utils.decorators import method_decorator
from django.views import View
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth.decorators import user_passes_test
from django.conf import settings # For accessing DEFAULT_FROM_EMAIL

from payments.forms.admin_reject_refund_form import AdminRejectRefundForm
from payments.models.HireRefundRequest import HireRefundRequest
from users.views.auth import is_admin
from mailer.utils import send_templated_email # Import the email utility

@method_decorator(user_passes_test(is_admin), name='dispatch')
class AdminRejectRefundView(View):
    """
    View for administrators to reject a HireRefundRequest.
    It allows the admin to provide a reason for rejection and
    optionally send an automated email to the user.
    """
    template_name = 'payments/admin_reject_refund_form.html'

    def get(self, request, pk, *args, **kwargs):
        """
        Handles GET requests to display the rejection form for a specific
        HireRefundRequest.
        """
        hire_refund_request = get_object_or_404(HireRefundRequest, pk=pk)

        # Pre-populate the form with existing rejection_reason if available
        form = AdminRejectRefundForm(instance=hire_refund_request)

        context = {
            'form': form,
            'hire_refund_request': hire_refund_request,
            'title': f"Reject Refund Request for Booking {hire_refund_request.hire_booking.booking_reference}",
        }
        return render(request, self.template_name, context)

    def post(self, request, pk, *args, **kwargs):
        """
        Handles POST requests to process the rejection form submission.
        Updates the refund request status, saves the rejection reason,
        and conditionally sends an email.
        """
        hire_refund_request = get_object_or_404(HireRefundRequest, pk=pk)
        form = AdminRejectRefundForm(request.POST, instance=hire_refund_request)

        print(f"DEBUG: AdminRejectRefundView POST for request PK: {pk}")

        if form.is_valid():
            print("DEBUG: Form is valid.")
            # Update the status to 'rejected'
            refund_request_instance = form.save(commit=False)
            refund_request_instance.status = 'rejected'
            refund_request_instance.processed_by = request.user
            refund_request_instance.processed_at = timezone.now()
            refund_request_instance.save()

            messages.success(request, f"Refund Request for booking '{hire_refund_request.hire_booking.booking_reference}' has been successfully rejected.")

            # --- Send User Rejection Email (Conditional) ---
            print(f"DEBUG: send_rejection_email checkbox value: {form.cleaned_data.get('send_rejection_email')}")
            if form.cleaned_data.get('send_rejection_email'):
                print("DEBUG: 'send_rejection_email' is checked. Attempting to send user email.")
                recipient_email = refund_request_instance.request_email
                if not recipient_email and refund_request_instance.driver_profile and refund_request_instance.driver_profile.user:
                    recipient_email = refund_request_instance.driver_profile.user.email

                print(f"DEBUG: Determined user recipient email: {recipient_email}")

                if recipient_email:
                    user_email_context = {
                        'refund_request': refund_request_instance,
                        'admin_email': settings.DEFAULT_FROM_EMAIL,
                    }
                    try:
                        print(f"DEBUG: Calling send_templated_email for user {recipient_email} with template 'mailer/user_refund_request_rejected.html'")
                        send_templated_email(
                            recipient_list=[recipient_email],
                            subject=f"Update: Your Refund Request for Booking {hire_refund_request.hire_booking.booking_reference} Has Been Rejected",
                            template_name='user_refund_request_rejected.html',
                            context=user_email_context,
                            driver_profile=refund_request_instance.driver_profile,
                            booking=refund_request_instance.hire_booking
                        )
                        print("DEBUG: User email send_templated_email call completed.")
                        messages.info(request, "Automated rejection email sent to the user.")
                    except Exception as e:
                        messages.warning(request, f"Failed to send user rejection email: {e}")
                        print(f"ERROR: Failed to send user rejection email for refund request {pk}: {e}")
                else:
                    messages.warning(request, "Could not send automated rejection email to user: No recipient email found.")
                    print(f"DEBUG: No user recipient email found for refund request {pk}.")

            # --- Send Admin Rejection Notification Email (Always) ---
            print("DEBUG: Attempting to send admin rejection notification email.")
            admin_recipient_list = [settings.DEFAULT_FROM_EMAIL] # Send to the default admin email
            if hasattr(settings, 'ADMINS') and settings.ADMINS:
                # Add all ADMINS emails to the recipient list
                for name, email in settings.ADMINS:
                    if email not in admin_recipient_list: # Avoid duplicates
                        admin_recipient_list.append(email)

            admin_email_context = {
                'refund_request': refund_request_instance,
                'admin_email': settings.DEFAULT_FROM_EMAIL,
                'admin_refund_link': request.build_absolute_uri(
                    redirect('dashboard:edit_hire_refund_request', pk=refund_request_instance.pk).url
                ),
            }
            try:
                print(f"DEBUG: Calling send_templated_email for admin(s) {admin_recipient_list} with template 'mailer/admin_refund_request_rejected.html'")
                send_templated_email(
                    recipient_list=admin_recipient_list,
                    subject=f"Refund Request {hire_refund_request.hire_booking.booking_reference} Has Been Rejected",
                    template_name='admin_refund_request_rejected.html', # Corrected template path
                    context=admin_email_context,
                    # No driver_profile or booking needed for admin notification, as it's in context
                )
                print("DEBUG: Admin email send_templated_email call completed.")
                messages.info(request, "Admin notification email sent regarding the rejection.")
            except Exception as e:
                messages.error(request, f"Failed to send admin rejection notification email: {e}")
                print(f"ERROR: Failed to send admin rejection notification email for refund request {pk}: {e}")


            return redirect('dashboard:admin_hire_refund_management')
        else:
            print(f"DEBUG: Form is NOT valid. Errors: {form.errors}")
            # If the form is not valid, re-render the form with errors
            messages.error(request, "Please correct the errors below.")
            context = {
                'form': form,
                'hire_refund_request': hire_refund_request,
                'title': f"Reject Refund Request for Booking {hire_refund_request.hire_booking.booking_reference}",
            }
            return render(request, self.template_name, context)
