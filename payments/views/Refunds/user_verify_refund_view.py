from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.urls import reverse
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
import uuid
from decimal import Decimal

from django.conf import settings
from django.http import Http404

from payments.models.RefundRequest import RefundRequest
# Import both refund calculation utilities
from payments.utils.hire_refund_calc import calculate_hire_refund_amount
from payments.utils.service_refund_calc import calculate_service_refund_amount
from mailer.utils import send_templated_email

# Import booking models to check instance type for email sending
from hire.models import HireBooking, DriverProfile
from service.models import ServiceBooking, ServiceProfile

# Helper function to convert Decimal objects to float recursively
def _convert_decimals_to_float(obj):
    """
    Recursively converts Decimal objects within a dictionary or list to float.
    """
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: _convert_decimals_to_float(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_convert_decimals_to_float(elem) for elem in obj]
    else:
        return obj


class UserVerifyRefundView(View):
    """
    Handles the verification of a user's refund request via a unique token sent in email.
    Updates the RefundRequest status from 'unverified' to 'pending' upon successful verification.
    Also sends an admin notification email after successful verification.
    This view is generalized to handle both HireBookings and ServiceBookings.
    """
    def get(self, request, *args, **kwargs):
        print("--- UserVerifyRefundView: GET request received ---")
        token_str = request.GET.get('token')
        print(f"Token string received: {token_str}")

        if not token_str:
            print("ERROR: Token string is missing.")
            messages.error(request, "Verification link is missing a token.")
            return redirect(reverse('core:index'))

        try:
            verification_token = uuid.UUID(token_str)
            print(f"Parsed UUID token: {verification_token}")
        except ValueError:
            print("ERROR: Invalid verification token format.")
            messages.error(request, "Invalid verification token format.")
            return redirect(reverse('core:index'))

        try:
            print(f"Attempting to retrieve RefundRequest with token: {verification_token}")
            refund_request = get_object_or_404(RefundRequest, verification_token=verification_token)
            print(f"RefundRequest found: ID={refund_request.pk}, Current Status={refund_request.status}")

            if refund_request.status != 'unverified':
                print(f"INFO: Refund request (ID: {refund_request.pk}) is already '{refund_request.status}'. Redirecting to verified page.")
                messages.info(request, "This refund request has already been verified or processed.")
                return redirect(reverse('payments:user_verified_refund'))

            token_validity_hours = 24 # Example validity period
            print(f"Checking token validity. Token created at: {refund_request.token_created_at}, Current time: {timezone.now()}")
            if (timezone.now() - refund_request.token_created_at) > timedelta(hours=token_validity_hours):
                print("ERROR: Verification link has expired.")
                messages.error(request, "The verification link has expired. Please submit a new refund request.")
                # Redirect to the main refund request form (generalized)
                return redirect(reverse('payments:user_refund_request_form')) # Assuming a generic URL name for the form

            print(f"Updating refund request status from '{refund_request.status}' to 'pending'.")
            refund_request.status = 'pending'
            refund_request.save()
            print(f"RefundRequest (ID: {refund_request.pk}) status updated and saved successfully to '{refund_request.status}'.")

            refund_policy_snapshot = {}
            if refund_request.payment and refund_request.payment.refund_policy_snapshot:
                refund_policy_snapshot = refund_request.payment.refund_policy_snapshot
            print(f"Refund policy snapshot used: {refund_policy_snapshot}")


            # Determine which refund calculation utility to use based on booking type
            calculated_refund_result = {'entitled_amount': Decimal('0.00'), 'details': 'No calculation performed.'}
            booking_reference_for_email = "N/A"
            booking_object = None
            customer_profile_object = None
            admin_link_name = None # To store the name of the admin URL pattern

            if refund_request.hire_booking:
                print("Booking type: Hire Booking")
                calculated_refund_result = calculate_hire_refund_amount(
                    booking=refund_request.hire_booking,
                    refund_policy_snapshot=refund_policy_snapshot,
                    cancellation_datetime=refund_request.requested_at
                )
                booking_reference_for_email = refund_request.hire_booking.booking_reference
                booking_object = refund_request.hire_booking
                customer_profile_object = refund_request.driver_profile
                admin_link_name = 'service:edit_refund_request' # Specific admin URL for hire
            elif refund_request.service_booking:
                print("Booking type: Service Booking")
                calculated_refund_result = calculate_service_refund_amount(
                    booking=refund_request.service_booking,
                    refund_policy_snapshot=refund_policy_snapshot,
                    cancellation_datetime=refund_request.requested_at
                )
                booking_reference_for_email = refund_request.service_booking.service_booking_reference
                booking_object = refund_request.service_booking
                customer_profile_object = refund_request.service_profile
                admin_link_name = 'dashboard:edit_service_refund_request' # Assuming new admin URL for service

            print(f"Calculated refund result (before Decimal conversion): {calculated_refund_result}")
            # Extract the actual amount and store the full result in JSONField
            calculated_refund_amount = calculated_refund_result.get('entitled_amount', Decimal('0.00'))

            # Convert all Decimal values within calculated_refund_result to float for JSON serialization
            json_compatible_calculation_details = _convert_decimals_to_float(calculated_refund_result)

            refund_request.refund_calculation_details = {
                'calculated_amount': float(calculated_refund_amount), # Ensure this is float
                'policy_snapshot_used': refund_policy_snapshot,
                'cancellation_datetime': refund_request.requested_at.isoformat(),
                'booking_type': 'hire' if refund_request.hire_booking else 'service' if refund_request.service_booking else 'unknown',
                'full_calculation_details': json_compatible_calculation_details # Store the converted dictionary
            }
            refund_request.amount_to_refund = calculated_refund_amount # Pre-fill for admin review
            print("Saving refund request with calculated details and amount_to_refund.")
            refund_request.save()
            print("Refund request saved with calculated details.")


            admin_refund_link = "#" # Default if no specific link found
            if admin_link_name:
                admin_refund_link = request.build_absolute_uri(
                    reverse(admin_link_name, args=[refund_request.pk])
                )
            print(f"Admin refund link: {admin_refund_link}")

            admin_email_context = {
                'refund_request': refund_request,
                'calculated_refund_amount': calculated_refund_amount,
                'admin_refund_link': admin_refund_link,
                'booking_reference': booking_reference_for_email, # Pass the dynamic reference
            }

            admin_recipient_list = [getattr(settings, 'ADMIN_EMAIL', settings.DEFAULT_FROM_EMAIL)]
            if not admin_recipient_list or admin_recipient_list[0] == settings.DEFAULT_FROM_EMAIL:
                admin_recipient_list = [settings.DEFAULT_FROM_EMAIL]
            print(f"Admin recipient list: {admin_recipient_list}")

            print("Attempting to send admin notification email.")
            send_templated_email(
                recipient_list=admin_recipient_list,
                subject=f"VERIFIED Refund Request for Booking {booking_reference_for_email} (ID: {refund_request.pk})",
                template_name='admin_refund_request_notification.html',
                context=admin_email_context,
                booking=booking_object, # Can be HireBooking or ServiceBooking instance
                driver_profile=customer_profile_object if isinstance(customer_profile_object, DriverProfile) else None,
                service_profile=customer_profile_object if isinstance(customer_profile_object, ServiceProfile) else None,
            )
            print("Admin notification email sent successfully.")

            messages.success(request, "Your refund request has been successfully verified!")
            print("Redirecting to user_verified_refund page.")
            return redirect(reverse('payments:user_verified_refund'))

        except Http404:
            print("EXCEPTION: Http404 - Refund request not found.")
            messages.error(request, "The refund request associated with this token does not exist.")
            return redirect(reverse('core:index'))
        except Exception as e:
            print(f"EXCEPTION: An unexpected error occurred during verification: {e}")
            messages.error(request, f"An unexpected error occurred during verification: {e}")
            return redirect(reverse('core:index'))
