# payments/views/HireRefunds/user_refund_request_view.py

from django.shortcuts import render, redirect
from django.views import View
from django.urls import reverse
from django.contrib import messages
from payments.forms.user_hire_refund_request_form import UserHireRefundRequestForm
from payments.models.HireRefundRequest import HireRefundRequest
# You'll need to import send_verification_email and send_admin_notification_email
# once those utility functions are created. For now, we'll just print a placeholder.
# from .utils import send_verification_email, send_admin_notification_email

class UserRefundRequestView(View):
    """
    Handles the user-facing refund request form.
    Allows users to submit a refund request by providing their booking reference and email.
    Upon successful submission, a HireRefundRequest instance is created with 'unverified' status.
    An email is then sent to the user for confirmation, and an admin notification is sent.
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
            # Save the HireRefundRequest instance.
            # The form's clean method has already linked hire_booking, driver_profile, and payment.
            # It also set the status to 'unverified' and is_admin_initiated to False.
            refund_request = form.save()

            # --- Placeholder for email sending logic ---
            # In a real application, you would generate a unique token for verification
            # and include it in the email.
            # Example: verification_token = generate_unique_token()
            #          refund_request.verification_token = verification_token # Add this field to your model
            #          refund_request.save()

            # Send verification email to the user
            # send_verification_email(refund_request)
            print(f"DEBUG: Sending verification email to {refund_request.request_email} for refund request {refund_request.pk}")

            # Send notification email to admin
            # send_admin_notification_email(refund_request)
            print(f"DEBUG: Sending admin notification for new refund request {refund_request.pk}")
            # --- End Placeholder ---

            messages.success(request, 'Your refund request has been submitted. Please check your email to confirm your request.')
            # Redirect to a confirmation page that tells the user to check their email
            return redirect(reverse('payments:user_confirmation_refund_request')) # Assuming this URL exists

        else:
            # If the form is not valid, re-render the template with errors
            context = {
                'form': form,
                'page_title': 'Request a Refund',
                'intro_text': 'Please correct the errors below and try again.',
            }
            return render(request, self.template_name, context)

