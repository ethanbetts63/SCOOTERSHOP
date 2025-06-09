import stripe
from django.shortcuts import redirect, get_object_or_404
from django.views import View
from django.utils.decorators import method_decorator
from django.contrib import messages
from django.db import transaction
from django.conf import settings
from decimal import Decimal
from django.utils import timezone
from django.contrib.auth.decorators import user_passes_test
from users.views.auth import is_admin
from payments.models import RefundRequest

@method_decorator(user_passes_test(is_admin), name='dispatch')
class ProcessRefundView(View): # Renamed class to be generic
    """
    Handles the processing of refund requests, initiating Stripe refunds.
    This view is generalized to process refunds for both HireBookings and ServiceBookings.
    """
    def post(self, request, pk, *args, **kwargs):
        print(f"DEBUG: ProcessRefundView - POST request received for refund_request PK: {pk}")
        refund_request = get_object_or_404(RefundRequest, pk=pk)
        print(f"DEBUG: ProcessRefundView - RefundRequest fetched: {refund_request.id}, Current Status: {refund_request.status}")

        # Determine the redirect URL for admin management based on booking type
        # This assumes separate admin views for hire and service refund management
        admin_management_redirect_url = 'payments:admin_refund_management' # Generic fallback

        # Basic validation checks
        print(f"DEBUG: ProcessRefundView - Checking refund_request status: {refund_request.status}")
        if refund_request.status not in ['approved', 'reviewed_pending_approval', 'unverified']: # Added 'unverified' for broader handling
            messages.error(request, f"Refund request is not in an approvable state. Current status: {refund_request.get_status_display()}.")
            print(f"DEBUG: ProcessRefundView - Validation failed: Invalid refund_request status: {refund_request.status}")
            return redirect(admin_management_redirect_url)

        print(f"DEBUG: ProcessRefundView - Checking associated payment for refund_request: {refund_request.id}")
        if not refund_request.payment:
            messages.error(request, "Cannot process refund: No associated payment found for this request.")
            print("DEBUG: ProcessRefundView - Validation failed: No associated payment.")
            return redirect(admin_management_redirect_url)

        print(f"DEBUG: ProcessRefundView - Checking amount_to_refund: {refund_request.amount_to_refund}")
        if refund_request.amount_to_refund is None or refund_request.amount_to_refund <= 0:
            messages.error(request, "Cannot process refund: No valid amount specified to refund.")
            print(f"DEBUG: ProcessRefundView - Validation failed: Invalid amount_to_refund: {refund_request.amount_to_refund}")
            return redirect(admin_management_redirect_url)

        print(f"DEBUG: ProcessRefundView - Checking Stripe Payment Intent ID: {refund_request.payment.stripe_payment_intent_id}")
        if not refund_request.payment.stripe_payment_intent_id:
            messages.error(request, "Cannot process refund: Associated payment has no Stripe Payment Intent ID.")
            print("DEBUG: ProcessRefundView - Validation failed: No Stripe Payment Intent ID.")
            return redirect(admin_management_redirect_url)

        # Set Stripe API key from Django settings
        stripe.api_key = settings.STRIPE_SECRET_KEY
        print("DEBUG: ProcessRefundView - Stripe API key set.")

        try:
            with transaction.atomic():
                amount_in_cents = int(refund_request.amount_to_refund * Decimal('100'))
                print(f"DEBUG: ProcessRefundView - Attempting to refund amount: {refund_request.amount_to_refund} (in cents: {amount_in_cents})")

                # Dynamically set metadata based on booking type
                booking_reference_for_metadata = "N/A"
                if refund_request.hire_booking:
                    booking_reference_for_metadata = refund_request.hire_booking.booking_reference
                    print(f"DEBUG: ProcessRefundView - Booking type: Hire, Reference: {booking_reference_for_metadata}")
                elif refund_request.service_booking:
                    booking_reference_for_metadata = refund_request.service_booking.service_booking_reference
                    print(f"DEBUG: ProcessRefundView - Booking type: Service, Reference: {booking_reference_for_metadata}")

                metadata = {
                    'refund_request_id': str(refund_request.pk), # Generic ID
                    'admin_user_id': str(request.user.pk),
                    'booking_reference': booking_reference_for_metadata,
                    'booking_type': 'hire' if refund_request.hire_booking else 'service' if refund_request.service_booking else 'unknown',
                }
                print(f"DEBUG: ProcessRefundView - Stripe Refund Metadata: {metadata}")
                print(f"DEBUG: ProcessRefundView - Calling Stripe Refund.create for payment_intent: {refund_request.payment.stripe_payment_intent_id}")

                # Create the Stripe refund
                stripe_refund = stripe.Refund.create(
                    payment_intent=refund_request.payment.stripe_payment_intent_id,
                    amount=amount_in_cents,
                    reason='requested_by_customer',
                    metadata=metadata
                )
                print(f"DEBUG: ProcessRefundView - Stripe Refund created successfully. Stripe Refund ID: {stripe_refund.id}, Status: {stripe_refund.status}")

                # Update RefundRequest status and details
                refund_request.status = 'refunded' # Changed from 'approved' to 'refunded' directly after Stripe success
                refund_request.processed_by = request.user
                refund_request.processed_at = timezone.now()
                refund_request.stripe_refund_id = stripe_refund.id
                refund_request.save()
                print(f"DEBUG: ProcessRefundView - RefundRequest updated in DB. New status: {refund_request.status}, Stripe Refund ID: {refund_request.stripe_refund_id}")

                messages.success(request, f"Refund for booking '{booking_reference_for_metadata}' initiated successfully with Stripe (ID: {stripe_refund.id}). Status updated to '{refund_request.get_status_display()}'.")
                return redirect(admin_management_redirect_url)

        except stripe.error.StripeError as e:
            error_message = f"Stripe error initiating refund: {e.user_message or e}"
            messages.error(request, error_message)
            refund_request.status = 'failed'
            refund_request.staff_notes = (refund_request.staff_notes or "") + f"\nStripe initiation failed: {e.user_message or e} at {timezone.now()}"
            refund_request.save()
            print(f"ERROR: ProcessRefundView - StripeError: {error_message}. RefundRequest status set to 'failed'.")
            return redirect(admin_management_redirect_url)
        except Exception as e:
            error_message = f"An unexpected error occurred: {e}"
            messages.error(request, error_message)
            refund_request.status = 'failed'
            refund_request.staff_notes = (refund_request.staff_notes or "") + f"\nUnexpected error during initiation: {e} at {timezone.now()}"
            refund_request.save()
            print(f"ERROR: ProcessRefundView - Unexpected Exception: {error_message}. RefundRequest status set to 'failed'.")
            return redirect(admin_management_redirect_url)

