# payments/views/HireRefunds/user_verify_refund.py

from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.urls import reverse
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
import uuid

from payments.models.HireRefundRequest import HireRefundRequest

class UserVerifyRefundView(View):
    """
    Handles the verification of a user's refund request via a unique token sent in email.
    Updates the HireRefundRequest status from 'unverified' to 'pending' upon successful verification.
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

            messages.success(request, "Your refund request has been successfully verified!")
            return redirect(reverse('payments:user_verified_refund')) # Redirect to the verified confirmation page

        except HireRefundRequest.DoesNotExist:
            messages.error(request, "The refund request associated with this token does not exist.")
            return redirect(reverse('core:index')) # Redirect to homepage or an error page
        except Exception as e:
            messages.error(request, f"An unexpected error occurred during verification: {e}")
            return redirect(reverse('core:index'))

