# payments/views/HireRefunds/user_refund_request_view.py

from django.shortcuts import render, redirect
from django.views import View
from django.urls import reverse
from django.contrib import messages
from django.conf import settings # To get ADMIN_EMAIL and other settings
from django.utils import timezone
import uuid # For generating UUID tokens
import logging # Import logging

from payments.forms.user_hire_refund_request_form import UserHireRefundRequestForm
from payments.models.HireRefundRequest import HireRefundRequest
from payments.hire_refund_calc import calculate_refund_amount # Import the calculation utility
from mailer.utils import send_templated_email # Import your email utility

# Get an instance of a logger
logger = logging.getLogger(__name__)

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

        print("DEBUG: UserRefundRequestView - POST request received.")
        logger.info("UserRefundRequestView - POST request received.")

        if form.is_valid():
            print("DEBUG: Form is valid.")
            logger.info("UserRefundRequestView - Form is valid.")

            # Save the HireRefundRequest instance.
            # The form's clean method has already linked hire_booking, driver_profile, and payment.
            # It also set the status to 'unverified' and is_admin_initiated to False.
            refund_request = form.save(commit=False) # Don't commit yet, we need to add token

            # Generate a unique verification token and timestamp
            refund_request.verification_token = uuid.uuid4()
            refund_request.token_created_at = timezone.now()
            print(f"DEBUG: Generated verification token: {refund_request.verification_token}")
            logger.debug(f"UserRefundRequestView - Generated verification token: {refund_request.verification_token}")

            refund_request.save() # Now save the instance with the token
            print(f"DEBUG: Refund request saved with ID: {refund_request.pk} and status: {refund_request.status}")
            logger.info(f"UserRefundRequestView - Refund request saved with ID: {refund_request.pk} and status: {refund_request.status}")

            # --- Send verification email to the user ---
            verification_link = request.build_absolute_uri(
                reverse('payments:user_verify_refund') + f'?token={str(refund_request.verification_token)}'
            )
            print(f"DEBUG: User verification link: {verification_link}")
            logger.debug(f"UserRefundRequestView - User verification link: {verification_link}")

            # Assuming you have a refund policy URL in your settings or core app
            refund_policy_link = request.build_absolute_uri(reverse('core:returns')) # Adjust 'core:returns' as per your actual URL name
            admin_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'admin@example.com') # Or a specific admin email

            user_email_context = {
                'refund_request': refund_request,
                'verification_link': verification_link,
                'refund_policy_link': refund_policy_link,
                'admin_email': admin_email,
            }
            print(f"DEBUG: Sending user email to: {refund_request.request_email}")
            logger.info(f"UserRefundRequestView - Sending user email to: {refund_request.request_email}")

            user_email_sent = send_templated_email(
                recipient_list=[refund_request.request_email],
                subject=f"Confirm Your Refund Request for Booking {refund_request.hire_booking.booking_reference}",
                template_name='emails/user_refund_request_verification.html',
                context=user_email_context,
                driver_profile=refund_request.driver_profile,
                booking=refund_request.hire_booking
            )
            print(f"DEBUG: User email sent status: {user_email_sent}")
            logger.info(f"UserRefundRequestView - User email sent status: {user_email_sent}")


            # --- Send notification email to admin ---
            # Calculate the entitled refund amount for the admin notification
            # Use the refund_policy_snapshot from the payment model
            refund_policy_snapshot = refund_request.payment.refund_policy_snapshot
            calculated_refund_amount = calculate_refund_amount(
                booking=refund_request.hire_booking,
                refund_policy_snapshot=refund_policy_snapshot,
                cancellation_datetime=refund_request.requested_at # Use the request timestamp as cancellation time
            )

            # FIX: Corrected the admin refund link based on the provided URL patterns
            # Assuming 'dashboard' is the app_name for the admin-related URLs
            admin_refund_link = request.build_absolute_uri(
                reverse('dashboard:edit_hire_refund_request', args=[refund_request.pk])
            )
            print(f"DEBUG: Admin refund link: {admin_refund_link}")
            logger.debug(f"UserRefundRequestView - Admin refund link: {admin_refund_link}")

            admin_email_context = {
                'refund_request': refund_request,
                'calculated_refund_amount': calculated_refund_amount,
                'admin_refund_link': admin_refund_link, # Now re-enabled
            }

            # Assuming you have a list of admin emails in settings or a specific one
            admin_recipient_list = [getattr(settings, 'ADMIN_EMAIL', 'admin@example.com')] # Define ADMIN_EMAIL in settings.py
            if not admin_recipient_list or admin_recipient_list[0] == 'admin@example.com':
                 # Fallback if ADMIN_EMAIL is not set or is default
                admin_recipient_list = [settings.DEFAULT_FROM_EMAIL]

            print(f"DEBUG: Sending admin email to: {admin_recipient_list}")
            logger.info(f"UserRefundRequestView - Sending admin email to: {admin_recipient_list}")

            admin_email_sent = send_templated_email(
                recipient_list=admin_recipient_list,
                subject=f"NEW Refund Request for Booking {refund_request.hire_booking.booking_reference} (ID: {refund_request.pk})",
                template_name='emails/admin_refund_request_notification.html',
                context=admin_email_context,
                driver_profile=refund_request.driver_profile,
                booking=refund_request.hire_booking
            )
            print(f"DEBUG: Admin email sent status: {admin_email_sent}")
            logger.info(f"UserRefundRequestView - Admin email sent status: {admin_email_sent}")

            messages.success(request, 'Your refund request has been submitted. Please check your email to confirm your request.')
            print("DEBUG: Redirecting to user confirmation page.")
            logger.info("UserRefundRequestView - Redirecting to user confirmation page.")
            return redirect(reverse('payments:user_confirmation_refund_request'))

        else:
            print("DEBUG: Form is NOT valid. Errors:")
            logger.warning("UserRefundRequestView - Form is NOT valid.")
            for field, errors in form.errors.items():
                print(f"DEBUG:   {field}: {', '.join(errors)}")
                logger.warning(f"UserRefundRequestView - Form error - {field}: {', '.join(errors)}")
            # If the form is not valid, re-render the template with errors
            context = {
                'form': form,
                'page_title': 'Request a Refund',
                'intro_text': 'Please correct the errors below and try again.',
            }
            return render(request, self.template_name, context)

