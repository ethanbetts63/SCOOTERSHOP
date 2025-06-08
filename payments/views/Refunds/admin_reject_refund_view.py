from django.shortcuts import render, redirect, get_object_or_404
from django.utils.decorators import method_decorator
from django.views import View
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth.decorators import user_passes_test
from django.conf import settings
from django.urls import reverse

from payments.forms.admin_reject_refund_form import AdminRejectRefundForm
from payments.models.RefundRequest import RefundRequest
from users.views.auth import is_admin
from mailer.utils import send_templated_email

# Import booking models to access their specific fields and types
from hire.models import HireBooking, DriverProfile
from service.models import ServiceBooking, ServiceProfile


@method_decorator(user_passes_test(is_admin), name='dispatch')
class AdminRejectRefundView(View):
    """
    View for administrators to reject a RefundRequest.
    It allows the admin to provide a reason for rejection and
    optionally send an automated email to the user.
    This view is generalized to handle both HireBookings and ServiceBookings.
    """
    template_name = 'payments/admin_reject_refund_form.html'

    def get(self, request, pk, *args, **kwargs):
        """
        Handles GET requests to display the rejection form for a specific
        RefundRequest.
        """
        refund_request = get_object_or_404(RefundRequest, pk=pk)

        # Dynamically determine the booking reference for the title
        booking_reference = "N/A"
        if refund_request.hire_booking:
            booking_reference = refund_request.hire_booking.booking_reference
        elif refund_request.service_booking:
            booking_reference = refund_request.service_booking.service_booking_reference

        form = AdminRejectRefundForm(instance=refund_request)

        context = {
            'form': form,
            'refund_request': refund_request, # Use generic name
            'title': f"Reject Refund Request for Booking {booking_reference}",
        }
        return render(request, self.template_name, context)

    def post(self, request, pk, *args, **kwargs):
        """
        Handles POST requests to process the rejection form submission.
        Updates the refund request status, saves the rejection reason,
        and conditionally sends an email.
        """
        refund_request_instance = get_object_or_404(RefundRequest, pk=pk)
        form = AdminRejectRefundForm(request.POST, instance=refund_request_instance)

        # Determine booking reference and objects for emails/redirects dynamically
        booking_reference_for_email = "N/A"
        booking_object = None
        customer_profile_object = None
        admin_management_redirect_url = 'dashboard:admin_refund_management_list' # Generic fallback
        admin_edit_link_name = None # To store the name of the admin URL pattern

        if refund_request_instance.hire_booking:
            booking_reference_for_email = refund_request_instance.hire_booking.booking_reference
            booking_object = refund_request_instance.hire_booking
            customer_profile_object = refund_request_instance.driver_profile
            admin_management_redirect_url = 'payments:admin_refund_management'
            admin_edit_link_name = 'dashboard:edit_hire_refund_request'
        elif refund_request_instance.service_booking:
            booking_reference_for_email = refund_request_instance.service_booking.service_booking_reference
            booking_object = refund_request_instance.service_booking
            customer_profile_object = refund_request_instance.service_profile
            admin_management_redirect_url = 'dashboard:admin_service_refund_management' # Assuming this exists
            admin_edit_link_name = 'dashboard:edit_service_refund_request' # Assuming this exists


        if form.is_valid():
            refund_request_instance = form.save(commit=False)
            refund_request_instance.status = 'rejected'
            refund_request_instance.processed_by = request.user
            refund_request_instance.processed_at = timezone.now()
            refund_request_instance.save()

            messages.success(request, f"Refund Request for booking '{booking_reference_for_email}' has been successfully rejected.")

            # --- Send user rejection email ---
            if form.cleaned_data.get('send_rejection_email'):
                recipient_email = refund_request_instance.request_email
                # Fallback to user email from profile if request_email not set
                if not recipient_email:
                    if isinstance(customer_profile_object, DriverProfile) and customer_profile_object.user:
                        recipient_email = customer_profile_object.user.email
                    elif isinstance(customer_profile_object, ServiceProfile) and customer_profile_object.user:
                        recipient_email = customer_profile_object.user.email

                if recipient_email:
                    user_email_context = {
                        'refund_request': refund_request_instance,
                        'admin_email': settings.DEFAULT_FROM_EMAIL,
                        'booking_reference': booking_reference_for_email,
                    }
                    try:
                        send_templated_email(
                            recipient_list=[recipient_email],
                            subject=f"Update: Your Refund Request for Booking {booking_reference_for_email} Has Been Rejected",
                            template_name='user_refund_request_rejected.html',
                            context=user_email_context,
                            booking=booking_object, # Pass generic booking object
                            driver_profile=customer_profile_object if isinstance(customer_profile_object, DriverProfile) else None,
                            service_profile=customer_profile_object if isinstance(customer_profile_object, ServiceProfile) else None,
                        )
                        messages.info(request, "Automated rejection email sent to the user.")
                    except Exception as e:
                        messages.warning(request, f"Failed to send user rejection email: {e}")
                else:
                    messages.warning(request, "Could not send automated rejection email to user: No recipient email found.")

            # --- Send admin notification email ---
            admin_recipient_list = [settings.DEFAULT_FROM_EMAIL]
            if hasattr(settings, 'ADMINS') and settings.ADMINS:
                for name, email in settings.ADMINS:
                    if email not in admin_recipient_list:
                        admin_recipient_list.append(email)

            admin_refund_link = "#" # Default
            if admin_edit_link_name:
                admin_refund_link = request.build_absolute_uri(
                    reverse(admin_edit_link_name, args=[refund_request_instance.pk])
                )

            admin_email_context = {
                'refund_request': refund_request_instance,
                'admin_email': settings.DEFAULT_FROM_EMAIL,
                'admin_refund_link': admin_refund_link,
                'booking_reference': booking_reference_for_email,
            }
            try:
                send_templated_email(
                    recipient_list=admin_recipient_list,
                    subject=f"Refund Request {booking_reference_for_email} (ID: {refund_request_instance.pk}) Has Been Rejected",
                    template_name='admin_refund_request_rejected.html',
                    context=admin_email_context,
                    booking=booking_object, # Pass generic booking object
                    driver_profile=customer_profile_object if isinstance(customer_profile_object, DriverProfile) else None,
                    service_profile=customer_profile_object if isinstance(customer_profile_object, ServiceProfile) else None,
                )
                messages.info(request, "Admin notification email sent regarding the rejection.")
            except Exception as e:
                messages.error(request, f"Failed to send admin rejection notification email: {e}")


            return redirect(admin_management_redirect_url) # Redirect to appropriate admin list view
        else:
            messages.error(request, "Please correct the errors below.")
            context = {
                'form': form,
                'refund_request': refund_request_instance, # Use generic name
                'title': f"Reject Refund Request for Booking {booking_reference_for_email}",
            }
            return render(request, self.template_name, context)

