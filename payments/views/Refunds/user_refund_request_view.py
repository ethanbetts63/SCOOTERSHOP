from django.shortcuts import render, redirect
from django.views import View
from django.urls import reverse
from django.contrib import messages
from django.conf import settings
from django.utils import timezone
import uuid

# Import the generalized RefundRequestForm
from payments.forms.user_refund_request_form import RefundRequestForm
from payments.models.RefundRequest import RefundRequest
from mailer.utils import send_templated_email
from service.models import ServiceProfile
from hire.models import DriverProfile


class UserRefundRequestView(View):
    """
    Handles the user-facing refund request form.
    Allows users to submit a refund request by providing their booking reference and email.
    Upon successful submission, a RefundRequest instance is created with 'unverified' status.
    An email is then sent to the user for confirmation.
    This view is generalized to handle both HireBookings and ServiceBookings.
    """
    template_name = 'payments/user_refund_request.html' # Renamed template for generality

    def get(self, request, *args, **kwargs):
        """
        Displays the empty refund request form.
        """
        form = RefundRequestForm() # Use the generalized form
        context = {
            'form': form,
            'page_title': 'Request a Refund',
            'intro_text': 'Please enter your booking details to request a refund. An email will be sent to confirm your request.',
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        """
        Processes the submitted refund request form.
        Validates the booking reference and email, creates the refund request,
        and triggers email notifications.
        """
        form = RefundRequestForm(request.POST) # Use the generalized form

        if form.is_valid():
            refund_request = form.save(commit=False)

            # Ensure verification token and creation time are set
            # This is already handled in RefundRequest.save() if not self.verification_token
            # However, explicitly setting here before save ensures it's available for email context immediately
            if not refund_request.verification_token:
                refund_request.verification_token = uuid.uuid4()
            if not refund_request.token_created_at:
                refund_request.token_created_at = timezone.now()

            refund_request.save()

            verification_link = request.build_absolute_uri(
                reverse('payments:user_verify_refund') + f'?token={str(refund_request.verification_token)}'
            )

            refund_policy_link = request.build_absolute_uri(reverse('core:returns'))
            admin_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'admin@example.com')

            # Determine booking reference for email subject dynamically
            booking_reference_for_email = "N/A"
            booking_object = None
            customer_profile_object = None

            if refund_request.hire_booking:
                booking_reference_for_email = refund_request.hire_booking.booking_reference
                booking_object = refund_request.hire_booking
                customer_profile_object = refund_request.driver_profile
            elif refund_request.service_booking:
                booking_reference_for_email = refund_request.service_booking.service_booking_reference
                booking_object = refund_request.service_booking
                customer_profile_object = refund_request.service_profile

            user_email_context = {
                'refund_request': refund_request,
                'verification_link': verification_link,
                'refund_policy_link': refund_policy_link,
                'admin_email': admin_email,
                'booking_reference': booking_reference_for_email, # Pass the dynamic reference
            }

            # Dynamically pass booking and profile to send_templated_email
            send_templated_email(
                recipient_list=[refund_request.request_email],
                subject=f"Confirm Your Refund Request for Booking {booking_reference_for_email}",
                template_name='user_refund_request_verification.html',
                context=user_email_context,
                # Pass the correct related objects for mailer's context processing
                booking=booking_object, # Can be HireBooking or ServiceBooking instance
                driver_profile=customer_profile_object if isinstance(customer_profile_object, DriverProfile) else None,
                service_profile=customer_profile_object if isinstance(customer_profile_object, ServiceProfile) else None,
            )

            messages.success(request, 'Your refund request has been submitted. Please check your email to confirm your request.')
            return redirect(reverse('payments:user_confirmation_refund_request'))

        else:
            context = {
                'form': form,
                'page_title': 'Request a Refund',
                'intro_text': 'Please correct the errors below and try again.',
            }
            return render(request, self.template_name, context)

