from django.shortcuts import render, redirect
from django.views import View
from django.urls import reverse
from django.contrib import messages
from django.conf import settings
from django.utils import timezone
import uuid

from payments.forms.user_hire_refund_request_form import UserHireRefundRequestForm
from payments.models.HireRefundRequest import HireRefundRequest
from mailer.utils import send_templated_email


class UserRefundRequestView(View):
    """
    Handles the user-facing refund request form.
    Allows users to submit a refund request by providing their booking reference and email.
    Upon successful submission, a HireRefundRequest instance is created with 'unverified' status.
    An email is then sent to the user for confirmation.
    """
    template_name = 'payments/user_refund_request_hire.html'

    def get(self, request, *args, **kwargs):
        """
        Displays the empty refund request form.
        """
        form = UserHireRefundRequestForm()
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
        form = UserHireRefundRequestForm(request.POST)

        if form.is_valid():
            refund_request = form.save(commit=False)

            refund_request.verification_token = uuid.uuid4()
            refund_request.token_created_at = timezone.now()

            refund_request.save()

            verification_link = request.build_absolute_uri(
                reverse('payments:user_verify_refund') + f'?token={str(refund_request.verification_token)}'
            )

            refund_policy_link = request.build_absolute_uri(reverse('core:returns'))
            admin_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'admin@example.com')

            user_email_context = {
                'refund_request': refund_request,
                'verification_link': verification_link,
                'refund_policy_link': refund_policy_link,
                'admin_email': admin_email,
            }

            send_templated_email(
                recipient_list=[refund_request.request_email],
                subject=f"Confirm Your Refund Request for Booking {refund_request.hire_booking.booking_reference}",
                template_name='user_refund_request_verification.html',
                context=user_email_context,
                driver_profile=refund_request.driver_profile,
                booking=refund_request.hire_booking
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
