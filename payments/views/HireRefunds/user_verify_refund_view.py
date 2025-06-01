# payments/views/HireRefunds/user_verify_refund.py

from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.urls import reverse
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
import uuid

from django.conf import settings # To get ADMIN_EMAIL and other settings

from payments.models.HireRefundRequest import HireRefundRequest
from payments.hire_refund_calc import calculate_refund_amount # Import the calculation utility
from mailer.utils import send_templated_email # Import your email utility


class UserVerifyRefundView(View):
    """
    Handles the verification of a user's refund request via a unique token sent in email.
    Updates the HireRefundRequest status from 'unverified' to 'pending' upon successful verification.
    Also sends an admin notification email after successful verification.
    """
    def get(self, request, *args, **kwargs):
        token_str = request.GET.get('token')

        if not token_str:
            messages.error(request, "Verification link is missing a token.")
            return redirect(reverse('core:index')) # Redirect to homepage or an error page

        try:
            verification_token = uuid.UUID(token_str)
        except ValueError:
            messages.error(request, "Invalid verification token format.")
            return redirect(reverse('core:index'))

        try:
            refund_request = get_object_or_404(HireRefundRequest, verification_token=verification_token)

            # Check if the request is already verified or processed
            if refund_request.status != 'unverified':
                messages.info(request, "This refund request has already been verified or processed.")
                return redirect(reverse('payments:user_verified_refund')) # Redirect to the 'already verified' page

            # Check if the token has expired (e.g., 24 hours validity)
            token_validity_hours = 24 # Define token validity period
            if (timezone.now() - refund_request.token_created_at) > timedelta(hours=token_validity_hours):
                messages.error(request, "The verification link has expired. Please submit a new refund request.")
                # Optionally, you might want to mark this request as 'expired' or similar
                # refund_request.status = 'expired'
                # refund_request.save()
                return redirect(reverse('payments:user_refund_request_hire')) # Redirect to the request form

            # If all checks pass, update the status to 'pending'
            refund_request.status = 'pending'
            refund_request.save()

            # --- Send notification email to admin after successful user verification ---
            # Calculate the entitled refund amount for the admin notification
            # Use the refund_policy_snapshot from the payment model
            refund_policy_snapshot = refund_request.payment.refund_policy_snapshot
            calculated_refund_amount = calculate_refund_amount(
                booking=refund_request.hire_booking,
                refund_policy_snapshot=refund_policy_snapshot,
                cancellation_datetime=refund_request.requested_at # Use the request timestamp as cancellation time
            )

            admin_refund_link = request.build_absolute_uri(
                reverse('dashboard:edit_hire_refund_request', args=[refund_request.pk])
            )

            admin_email_context = {
                'refund_request': refund_request,
                'calculated_refund_amount': calculated_refund_amount,
                'admin_refund_link': admin_refund_link,
            }

            # Assuming you have a list of admin emails in settings or a specific one
            admin_recipient_list = [getattr(settings, 'ADMIN_EMAIL', settings.DEFAULT_FROM_EMAIL)]
            if not admin_recipient_list or admin_recipient_list[0] == settings.DEFAULT_FROM_EMAIL:
                 # Fallback if ADMIN_EMAIL is not set or is default
                admin_recipient_list = [settings.DEFAULT_FROM_EMAIL]

            send_templated_email(
                recipient_list=admin_recipient_list,
                subject=f"VERIFIED Refund Request for Booking {refund_request.hire_booking.booking_reference} (ID: {refund_request.pk})",
                template_name='admin_refund_request_notification.html',
                context=admin_email_context,
                driver_profile=refund_request.driver_profile,
                booking=refund_request.hire_booking
            )

            messages.success(request, "Your refund request has been successfully verified!")
            return redirect(reverse('payments:user_verified_refund')) # Redirect to the verified confirmation page

        except HireRefundRequest.DoesNotExist:
            messages.error(request, "The refund request associated with this token does not exist.")
            return redirect(reverse('core:index')) # Redirect to homepage or an error page
        except Exception as e:
            messages.error(request, f"An unexpected error occurred during verification: {e}")
            return redirect(reverse('core:index'))
